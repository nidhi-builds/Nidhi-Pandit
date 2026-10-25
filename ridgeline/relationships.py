"""Normal relationships are fitted on eligible baselines, never station IDs."""
import numpy as np
import pandas as pd
from .checks import intervals
from .config import CHANNELS, BIAS_FLOORS
from .gps import distance_m


def solar_elevation(times, lat, lon):
    """NOAA general solar equations; UTC and east-positive longitude."""
    times = pd.DatetimeIndex(times)
    hour = times.hour.to_numpy() + times.minute.to_numpy() / 60
    gamma = 2 * np.pi / 365 * (times.dayofyear.to_numpy() - 1 + (hour - 12) / 24)
    equation = 229.18 * (.000075 + .001868 * np.cos(gamma) - .032077 * np.sin(gamma)
                       - .014615 * np.cos(2 * gamma) - .040849 * np.sin(2 * gamma))
    declination = (.006918 - .399912 * np.cos(gamma) + .070257 * np.sin(gamma)
                   - .006758 * np.cos(2 * gamma) + .000907 * np.sin(2 * gamma)
                   - .002697 * np.cos(3 * gamma) + .00148 * np.sin(3 * gamma))
    angle = np.radians((hour * 60 + equation + 4 * lon) / 4 - 180)
    sine = np.sin(np.radians(lat)) * np.sin(declination) + np.cos(np.radians(lat)) * np.cos(declination) * np.cos(angle)
    return np.degrees(np.arcsin(np.clip(sine, -1, 1)))


def hourly_data(pack, basic):
    hourly = {}
    for station, original in pack.weather.items():
        frame = original.copy()
        for candidate in basic:
            if candidate.station_id != station or not candidate.evidence.get('supported'):
                continue
            if candidate.issue in ('missing_data', 'out_of_range', 'flatline', 'spike'):
                columns = list(CHANNELS) if candidate.channel == 'all' else [candidate.channel]
                mask = frame._source.str.cat(frame._row.astype(str), sep=':').isin(candidate.row_refs)
                frame.loc[mask, columns] = np.nan
        frame = frame.loc[frame._time.notna()].drop_duplicates('_time', keep='first').set_index('_time')
        values = frame[list(CHANNELS)].resample('h').median()
        values['rain_mm'] = frame.rain_mm.resample('h').sum(min_count=1)
        hourly[station] = values
    return hourly


def references(pack, hourly, station, channel):
    target = hourly[station][channel]
    if target.dropna().empty:
        return []
    end = target.dropna().index[0] + pd.Timedelta(days=7)
    baseline = target.loc[target.index < end]
    if len(baseline) < 168 or baseline.notna().sum() < 118:
        return []
    choices = []
    for other in sorted(hourly):
        if other == station:
            continue
        paired = pd.concat([baseline, hourly[other][channel]], axis=1, keys=['target', 'peer']).reindex(baseline.index).dropna()
        if len(paired) < 118:
            continue
        correlation = paired.diff().dropna().corr().iloc[0, 1]
        threshold = .7 if channel == 'pressure_hpa' else .5 if channel in ('temp_c', 'rh_pct') else .3
        if not np.isfinite(correlation) or correlation < threshold:
            continue
        distance = float(distance_m(pack.stations.loc[station, 'lat'], pack.stations.loc[station, 'lon'],
                                    pack.stations.loc[other, 'lat'], pack.stations.loc[other, 'lon']))
        choices.append((distance, other))
    return [other for _, other in sorted(choices)[:3]]


def paired_residuals(hourly, station, peers, channel):
    target = hourly[station][channel]
    baseline_end = target.dropna().index[0] + pd.Timedelta(days=7)
    residuals = {}
    for peer in peers:
        ref = hourly[peer][channel].reindex(target.index)
        if channel == 'wind_kmh':
            residual = np.log(target.where(target >= 2) / ref.where(ref >= 2))
        else:
            residual = target - ref
        baseline = residual.loc[residual.index < baseline_end].dropna()
        residuals[peer] = residual - baseline.median()
    return pd.DataFrame(residuals), baseline_end


def hourly_runs(mask):
    selected = mask.index[mask.fillna(False)]
    if len(selected) == 0:
        return []
    group = pd.Series(selected, index=selected).diff().ne(pd.Timedelta(hours=1)).cumsum()
    return [(part.index[0], part.index[-1]) for _, part in pd.Series(True, index=selected).groupby(group)]


def native_event(pack, station, channel, issue, subtype, start, end, evidence, extra=None):
    frame = pack.weather[station]
    mask = frame._time.ge(start) & frame._time.lt(end + pd.Timedelta(hours=1))
    if extra is not None:
        mask &= extra
    return intervals(pack, station, channel, issue, subtype, mask, evidence)


def bias_events(pack, hourly, station, channel, peers):
    residuals, baseline_end = paired_residuals(hourly, station, peers, channel)
    combined = residuals.median(axis=1)
    baseline = residuals.loc[residuals.index < baseline_end]
    floor = np.log(1.4) if channel == 'wind_kmh' else BIAS_FLOORS[channel]
    thresholds = baseline.apply(lambda s: max(floor, 6 * 1.4826 * float((s - s.median()).abs().median())))
    high = residuals.gt(thresholds).sum(axis=1).ge(2)
    low = residuals.lt(-thresholds).sum(axis=1).ge(2)
    valid = residuals.notna().sum(axis=1).ge(2)
    result = []
    base_evidence = {'supported': True, 'references': peers, 'baseline_hours': int(baseline.notna().sum().min()),
                     'thresholds': {p: round(float(v), 4) for p, v in thresholds.items()},
                     'reason': f'Persistent {channel} departure from its own normal relationships with at least two suitable stations'}
    gradual_start = None
    if channel in ('temp_c', 'pressure_hpa'):
        daily = residuals.resample('D').median()
        derivative = daily.diff()
        minimum = BIAS_FLOORS[channel] / 14
        for direction in (1, -1):
            agreement = (derivative * direction).gt(minimum).sum(axis=1).ge(2)
            selected = agreement.index[agreement & (agreement.index >= baseline_end)]
            if len(selected):
                groups = pd.Series(selected, index=selected).diff().ne(pd.Timedelta(days=1)).cumsum()
                for _, dates in pd.Series(selected, index=selected).groupby(groups):
                    first, last = dates.iloc[0] - pd.Timedelta(days=1), dates.iloc[-1]
                    change = daily.loc[last].median() - daily.loc[first].median() if first in daily.index else 0
                    if len(dates) >= 6 and abs(change) >= BIAS_FLOORS[channel]:
                        gradual_start = first
                        evidence = dict(base_evidence, departure=round(float(change), 3), eligible_hours=int(valid.sum()))
                        result += native_event(pack, station, channel, 'sensor_bias', 'gradual', first, combined.index[-1], evidence)
                        break
    if gradual_start is None:
        for start, end in hourly_runs((high | low) & valid & (residuals.index >= baseline_end)):
            if end - start < pd.Timedelta(hours=23):
                continue
            evidence = dict(base_evidence, departure=round(float(combined.loc[start:end].median()), 3),
                            eligible_hours=int(valid.loc[start:end].sum()))
            result += native_event(pack, station, channel, 'sensor_bias', 'multiplicative' if channel == 'wind_kmh' else 'additive', start, end, evidence)
    if channel == 'temp_c':
        h = hourly[station]
        high_light = h.ghi_wm2.ge(400) & h.wind_kmh.le(5)
        dark = h.ghi_wm2.le(20)
        if dark.sum() >= 18 and (high_light & (h.index < baseline_end)).sum() >= 18:
            night_level = combined.where(dark).ffill().rolling(72, min_periods=1).median()
            excess = combined - night_level
            baseline_high = excess.loc[high_light & (h.index < baseline_end)].median()
            affected = high_light & excess.sub(baseline_high).ge(2) & (h.index >= baseline_end) & valid
            if affected.sum() >= 18 and affected.index[affected].normalize().nunique() >= 3:
                frame = pack.weather[station]
                extra = frame.ghi_wm2.ge(400) & frame.wind_kmh.le(5)
                for start, end in hourly_runs(affected):
                    result += native_event(pack, station, channel, 'sensor_bias', 'conditional', start, end,
                        dict(base_evidence, departure=round(float(excess.loc[start:end].median() - baseline_high), 3),
                             eligible_hours=int(affected.sum()), reason='Temperature excess increases in strong light and weak wind relative to baseline and night-time comparisons'), extra)
    return result


def rain_events(pack, hourly, station, peers):
    target = hourly[station]
    rain = pd.concat({p: hourly[p].rain_mm for p in peers}, axis=1).reindex(target.index)
    wet = rain.gt(0).sum(axis=1).ge(2)
    times = wet.index[wet]
    if len(times) == 0:
        return []
    groups = pd.Series(times, index=times).diff().ge(pd.Timedelta(hours=6)).cumsum()
    episodes = []
    for _, dates in pd.Series(times, index=times).groupby(groups):
        start, end = dates.iloc[0], dates.iloc[-1]
        totals = rain.loc[start:end].sum(min_count=1)
        usable = totals.index[totals >= 2].tolist()
        if len(usable) < 2:
            continue
        expected = float(totals.loc[usable].median())
        observed = float(target.loc[start:end, 'rain_mm'].sum(min_count=1))
        episodes.append((start, end, observed, expected, usable))
    failures = [e for e in episodes if np.isfinite(e[2]) and e[2] <= e[3] * .1]
    response = [e for e in episodes if e[2] >= e[3] * .25]
    result = []
    if len(failures) >= 3:
        for start, end, observed, expected, usable in failures:
            nonfreezing = bool(target.loc[start:end, 'temp_c'].ge(2).all())
            supported = bool(nonfreezing and response)
            result += native_event(pack, station, 'rain_mm', 'rainfall_underresponse', 'episodes', start, end,
                {'supported': supported, 'references': usable, 'observed_mm': round(observed, 3),
                 'reference_median_mm': round(expected, 3), 'failure_episodes': len(failures), 'response_episodes': len(response),
                 'threshold_ratio': .1, 'reason': 'Repeated rain underresponse compared with at least two stations; prior/recovered response and nonfreezing conditions required'})
    return result


def check_relationships(pack, basic):
    hourly = hourly_data(pack, basic)
    result = []
    for station in sorted(hourly):
        frame = pack.weather[station]
        valid_time = frame._time.notna()
        elevation = pd.Series(np.nan, index=frame.index)
        elevation.loc[valid_time] = solar_elevation(frame.loc[valid_time, '_time'], pack.stations.loc[station, 'lat'], pack.stations.loc[station, 'lon'])
        mismatch = elevation.lt(-6) & frame.ghi_wm2.gt(50)
        if mismatch.sum() * pack.stations.loc[station, 'logger_interval_min'] >= 180 and frame.loc[mismatch, '_time'].dt.date.nunique() >= 2:
            result += intervals(pack, station, 'ghi_wm2', 'sensor_bias', 'irradiance_timing', mismatch,
                {'supported': False, 'samples': int(mismatch.sum()), 'threshold_wm2': 50, 'solar_elevation_limit': -6,
                 'reason': 'Measured irradiance during astronomical night; verify time, location and irradiance before choosing an action'})
        for channel in ('temp_c', 'pressure_hpa', 'rh_pct', 'wind_kmh'):
            peers = references(pack, hourly, station, channel)
            if len(peers) >= 2:
                result += bias_events(pack, hourly, station, channel, peers)
            else:
                pack.diagnostics.append({'station_id': station, 'channel': channel, 'check': 'relationships',
                                         'reason': 'Fewer than two suitable references with seven baseline days; no automatic relational decision'})
        peers = references(pack, hourly, station, 'pressure_hpa')
        if len(peers) >= 2:
            result += rain_events(pack, hourly, station, peers)
    return result
