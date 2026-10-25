"""Candidates preserve row identities; final policy is in decisions.py."""
import numpy as np
import pandas as pd
from .config import CHANNELS, FLOORS
from .types import Candidate
from .gps import parse_nmea
from .reference import hourly_data,qualified_basic_peers


def row_refs(frame):
    return tuple(f'{source}:{row}' for source, row in zip(frame['_source'], frame['_row']))


def intervals(pack, station, channel, issue, subtype, mask, evidence):
    frame = pack.weather[station]
    selected = frame.loc[mask].copy()
    if selected.empty:
        return []
    cadence = pd.Timedelta(minutes=pack.stations.loc[station, 'logger_interval_min'])
    breaks = selected._row.diff().ne(1) | selected._segment.diff().ne(0) | selected._logger_time.diff().gt(cadence * 1.5) | selected._logger_time.isna()
    result = []
    for _, part in selected.groupby(breaks.cumsum(), sort=False):
        times = part._logger_time.dropna()
        result.append(Candidate(station, channel, issue, subtype,
            times.min() if len(times) else None, times.max() if len(times) else None, row_refs(part), dict(evidence)))
    return result


def verified_replay_segments(pack,station,frame):
    """Varied full-block identity plus independent valid GPS dates, not equality alone."""
    anchors=[]
    for line in pack.gps_lines.get(station,[]):
        try:
            logger,sentence=line.split(',',1);record=parse_nmea(sentence)
            if record and record['utc'] is not None and abs((pd.Timestamp(logger)-record['utc']).total_seconds())<=60:
                anchors.append(record['utc'])
        except (ValueError,TypeError):continue
    if len(anchors)<6:return set()
    anchors=pd.DatetimeIndex(anchors);verified=set()
    for segment,part in frame.groupby('_segment'):
        if segment==0 or len(part)<6 or not part[list(CHANNELS)].notna().all().all():continue
        if part[list(CHANNELS)].nunique().gt(1).sum()<2:continue
        earlier=frame.loc[frame._row<part._row.min()]
        matches=part.merge(earlier,on=['_logger_time',*CHANNELS],suffixes=('_new','_old'))
        matched=set(matches['_row_new'])
        gps_count=int(((anchors>=part._logger_time.min()) & (anchors<=part._logger_time.max())).sum())
        if len(matched)==len(part) and gps_count>=6:verified.add(segment)
    return verified


def check_basic(pack):
    result = []
    for station, frame in pack.weather.items():
        cadence = pd.Timedelta(minutes=pack.stations.loc[station, 'logger_interval_min'])
        replay_segments=verified_replay_segments(pack,station,frame)
        invalid_time = frame._logger_time.isna()
        result += intervals(pack, station, 'all', 'missing_data', 'timestamp', invalid_time,
                            {'supported': False, 'reason': 'Unparseable timestamp cannot be placed on a UTC interval'})
        for segment, part in frame.groupby('_segment'):
            times = part._time.dropna().sort_values().drop_duplicates()
            if len(times) > 1:
                for previous, current in zip(times.iloc[:-1], times.iloc[1:]):
                    missing = int(round((current - previous) / cadence)) - 1
                    if missing > 0 and (current - previous) % cadence == pd.Timedelta(0):
                        # Retransmitted fragments do not create gaps when those times already exist.
                        expected = pd.date_range(previous + cadence, current - cadence, freq=cadence)
                        if expected.isin(frame._time.dropna()).all():
                            continue
                        result.append(Candidate(station, 'all', 'missing_data', 'records', previous + cadence, current - cadence, (),
                            {'supported': True, 'missing_records': missing, 'cadence_minutes': cadence.total_seconds() / 60,
                             'time_basis': 'analysis grid', 'reason': f'{missing} expected records absent between observations'}))
        duplicate_mask = frame._logger_time.notna() & frame._logger_time.duplicated(keep=False)
        for timestamp, part in frame.loc[duplicate_mask].groupby('_logger_time', sort=True):
            if len(part) < 2:
                continue
            if part._time.nunique() == len(part) and part._time.ne(part._logger_time).any():
                continue  # GPS mapping established these as distinct observations, not duplicates.
            identical = part[list(CHANNELS)].nunique(dropna=False).le(1).all() and part[list(CHANNELS)].notna().all().all()
            # Distinct source segments with distinct values may be a clock collision, not retransmission.
            same_segment=part._segment.nunique()==1 and part._time.notna().all()
            replay=bool(set(part._segment.iloc[1:]).issubset(replay_segments))
            supported = bool(same_segment or identical and replay)
            if identical:
                result.append(Candidate(station, 'all', 'duplicate_data', 'identical', timestamp, timestamp, row_refs(part),
                    {'supported': supported, 'retain_row': int(part._row.iloc[0]), 'remove_rows': part._row.iloc[1:].astype(int).tolist(),
                     'reason': 'Identical observations share a logger timestamp; retain first source row only'}))
                result[-1].evidence['gps_supported_replay']=bool(replay and not same_segment)
            else:
                for channel in CHANNELS:
                    if part[channel].nunique(dropna=False) > 1:
                        result.append(Candidate(station, channel, 'duplicate_data', 'conflicting', timestamp, timestamp, row_refs(part),
                            {'supported': supported, 'reason': 'Conflicting observations share a logger label; verify source clock segments before selecting a value'}))
        for channel in CHANNELS:
            result += intervals(pack, station, channel, 'missing_data', 'values', frame[channel].isna(),
                                {'supported': True, 'reason': 'Missing or nonfinite channel value'})
        domains = {'rh_pct': (0, 100), 'wind_kmh': (0, np.inf), 'wind_dir_deg': (0, 360), 'rain_mm': (0, np.inf)}
        for channel, (low, high) in domains.items():
            invalid = frame[channel].notna() & ~frame[channel].between(low, high)
            result += intervals(pack, station, channel, 'out_of_range', 'domain', invalid,
                {'supported': True, 'lower_bound': low, 'upper_bound': high if np.isfinite(high) else None,
                 'reason': f'{channel} outside its defined measurement domain'})
        for channel in FLOORS:
            values = frame[channel]
            baseline = values.rolling(7, center=True, min_periods=5).median()
            residual = values - baseline
            scale = max(FLOORS[channel], float(residual.abs().median()) * 1.4826)
            if channel in ('temp_c', 'pressure_hpa', 'rh_pct'):
                spikes = residual.abs().gt(6 * scale)
                positions=np.flatnonzero(spikes.to_numpy())
                blocks=np.split(positions,np.flatnonzero(np.diff(positions)>1)+1) if len(positions) else []
                for block in blocks:
                    if len(block)>2:continue
                    first,last=int(block[0]),int(block[-1])
                    left=values.iloc[max(0,first-2):first];right=values.iloc[last+1:last+3]
                    if len(left)!=2 or len(right)!=2 or left.isna().any() or right.isna().any():continue
                    before,after=left.median(),right.median()
                    trend=((left.iloc[1]-left.iloc[0])+(right.iloc[1]-right.iloc[0]))/2
                    if abs(after-before-trend*(len(block)+2))>3*FLOORS[channel]:
                        continue  # A regime transition/recovery is not an excursion with return.
                    support = []
                    timestamps = frame.loc[block, '_time']
                    for other, peer in pack.weather.items():
                        if other == station:
                            continue
                        match = peer.loc[peer._time.isin(timestamps), channel]
                        series = peer[channel]
                        peer_residual = series - series.rolling(7, center=True, min_periods=5).median()
                        if len(match) == len(block) and peer_residual.loc[match.index].abs().lt(3 * FLOORS[channel]).all():
                            support.append(other)
                    result += intervals(pack, station, channel, 'spike', 'isolated', frame.index.isin(block),
                        {'supported': len(support) >= 2, 'departure': round(float(residual.loc[block].mean()), 3),
                         'threshold': round(6 * scale, 3), 'references': support,
                         'reason': f'Isolated {channel} excursion with return; comparison stations do not share the excursion'})
            groups = values.ne(values.shift()).cumsum()
            sizes = frame.groupby(groups, sort=False).size()
            for group in sizes.index[sizes * cadence >= pd.Timedelta(hours=12)]:
                part = frame.loc[groups.eq(group)]
                if len(part) * cadence < pd.Timedelta(hours=12) or part[channel].isna().all():
                    continue
                value = float(part[channel].iloc[0])
                if channel == 'wind_kmh' and value == 0:
                    continue
                reference_ids = []
                for other, peer in pack.weather.items():
                    if other == station:
                        continue
                    sample = peer.loc[peer._time.between(part._time.min(), part._time.max()), channel]
                    if len(sample) >= len(part) * .7 and sample.quantile(.95) - sample.quantile(.05) > 6 * FLOORS[channel]:
                        reference_ids.append(other)
                supported = len(reference_ids) >= 2
                if channel == 'rh_pct' and value >= 99:
                    sunny = part.ghi_wm2.ge(400) & part.temp_c.gt(15)
                    supported &= part.loc[sunny, '_time'].dt.date.nunique() >= 3
                result += intervals(pack, station, channel, 'flatline', 'constant', frame.index.isin(part.index),
                    {'supported': bool(supported), 'constant_value': value, 'samples': len(part), 'minimum_hours': 12,
                     'references': reference_ids, 'reason': f'{channel} unchanged for {len(part) * cadence.total_seconds() / 3600:.1f} hours; independent response evidence required'})
    clean=hourly_data(pack,result)
    cache={}
    for c in result:
        if c.issue not in ('flatline','spike'):continue
        key=(c.station_id,c.channel)
        if key not in cache:cache[key]=set(qualified_basic_peers(clean,*key))
        trustworthy=[p for p in c.evidence.get('references',[]) if p in cache[key]]
        c.evidence['references']=trustworthy
        c.evidence['minimum_reference_hours']=168
        c.evidence['supported']=bool(c.evidence['supported'] and len(trustworthy)>=2)
        if not c.evidence['supported']:c.evidence['reason']+='; fewer than two clean, baseline-qualified corroborating references'
    return result
