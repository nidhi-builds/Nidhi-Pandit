"""Candidates preserve row identities; final policy is in decisions.py."""
import numpy as np
import pandas as pd
from .config import CHANNELS
from .types import Candidate


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


def check_basic(pack):
    result = []
    for station, frame in pack.weather.items():
        cadence = pd.Timedelta(minutes=pack.stations.loc[station, 'logger_interval_min'])
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
        for timestamp, part in frame.loc[frame._logger_time.notna()].groupby('_logger_time', sort=True):
            if len(part) < 2:
                continue
            identical = part[list(CHANNELS)].nunique(dropna=False).le(1).all()
            # Distinct source segments with distinct values may be a clock collision, not retransmission.
            supported = bool(identical or part._segment.nunique() == 1 or part._time.nunique() == 1)
            if part._segment.nunique() > 1 and not identical and part._time.nunique() > 1:
                supported = False
            if part._segment.nunique() > 1 and not identical and part._time.equals(part._logger_time):
                supported = False
            if identical:
                result.append(Candidate(station, 'all', 'duplicate_data', 'identical', timestamp, timestamp, row_refs(part),
                    {'supported': supported, 'retain_row': int(part._row.iloc[0]), 'remove_rows': part._row.iloc[1:].astype(int).tolist(),
                     'reason': 'Identical observations share a logger timestamp; retain first source row only'}))
            else:
                for channel in CHANNELS:
                    if part[channel].nunique(dropna=False) > 1:
                        result.append(Candidate(station, channel, 'duplicate_data', 'conflicting', timestamp, timestamp, row_refs(part),
                            {'supported': supported, 'reason': 'Conflicting observations share a logger label; verify source clock segments before selecting a value'}))
        for channel in CHANNELS:
            result += intervals(pack, station, channel, 'missing_data', 'values', frame[channel].isna(),
                                {'supported': True, 'reason': 'Missing or nonfinite channel value'})
    return result
