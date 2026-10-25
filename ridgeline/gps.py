"""NMEA validation and conservative GPS-supported time mappings."""
from dataclasses import replace
from datetime import datetime
import math
import numpy as np
import pandas as pd
from .types import Candidate


def parse_nmea(sentence):
    try:
        body, check = sentence.strip().split('*')
        if not body.startswith('$') or len(check) != 2:
            return None
        checksum = 0
        for char in body[1:]:
            checksum ^= ord(char)
        if checksum != int(check, 16):
            return None
        fields = body[1:].split(',')
        kind = fields[0][-3:]
        if kind not in ('RMC', 'GGA'):
            return None
        if kind == 'RMC':
            if fields[2] != 'A':
                return None
            date = datetime.strptime(fields[9] + fields[1].split('.')[0], '%d%m%y%H%M%S')
            utc = pd.Timestamp(date) + pd.Timedelta(seconds=float('0.' + fields[1].split('.')[1]) if '.' in fields[1] else 0)
            lat, ns, lon, ew = fields[3:7]
        else:
            if int(fields[6]) <= 0:
                return None
            utc = None
            lat, ns, lon, ew = fields[2:6]
        if ns not in ('N', 'S') or ew not in ('E', 'W'):
            return None
        def coordinate(value, hemisphere):
            number = float(value)
            degrees = int(number // 100)
            minutes = number - degrees * 100
            if not 0 <= minutes < 60:
                raise ValueError('invalid coordinate minutes')
            return (degrees + minutes / 60) * (-1 if hemisphere in ('S', 'W') else 1)
        latitude, longitude = coordinate(lat, ns), coordinate(lon, ew)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return None
        return {'utc': utc, 'lat': latitude, 'lon': longitude, 'kind': kind}
    except (ValueError, IndexError, OverflowError):
        return None


def distance_m(lat1, lon1, lat2, lon2):
    lat1, lat2 = np.radians(lat1), np.radians(lat2)
    dlat, dlon = lat2 - lat1, np.radians(np.asarray(lon2) - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371000 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def audit_gps(pack):
    candidates = []
    for station, lines in pack.gps_lines.items():
        records, rejected = [], 0
        for row, line in enumerate(lines, 1):
            try:
                logger, sentence = line.split(',', 1)
                record = parse_nmea(sentence)
                if record is None:
                    rejected += 1
                elif record['utc'] is not None:
                    record.update(logger=pd.Timestamp(logger), row=row)
                    records.append(record)
            except (ValueError, TypeError):
                rejected += 1
        if rejected:
            pack.diagnostics.append({'station_id': station, 'check': 'gps', 'reason': f'{rejected} rejected GPS records'})
        if not records:
            continue
        g = pd.DataFrame(records)
        offsets = (g.logger - g.utc).dt.total_seconds()
        g['offset'] = offsets
        g['segment'] = (offsets.diff().abs().gt(60) | g.logger.diff().lt(pd.Timedelta(0))).cumsum()
        f = pack.weather[station]
        for segment, part in g.groupby('segment', sort=True):
            if len(part) < 6 or part.utc.max() - part.utc.min() < pd.Timedelta(hours=5):
                continue
            median = float(part.offset.median())
            mad = float((part.offset - median).abs().median())
            daily = part.set_index('utc').offset.resample('D').median().dropna()
            drift = len(daily) >= 3 and abs(float(np.median(np.diff(daily)))) >= 60
            if abs(median) <= 60 and not drift:
                continue
            # Logger GPS reception has second jitter; weather labels have minute precision.
            mask = f._logger_time.between(part.logger.min().floor('min'), part.logger.max().floor('min'))
            weather_segments = int(f._segment.max()) + 1 if len(f) else 0
            gps_segments = int(g.segment.max()) + 1
            if weather_segments > 1 and weather_segments == gps_segments:
                mask &= f._segment.eq(segment)
            scope = f._segment.eq(segment) if weather_segments == gps_segments else mask
            ambiguous = any(other != segment and max(part.logger.min(), otherpart.logger.min()) <= min(part.logger.max(), otherpart.logger.max())
                            for other, otherpart in g.groupby('segment') ) and weather_segments != gps_segments
            ambiguous |= f.loc[mask,'_segment'].nunique()>1
            correctable = mad <= 5 and not drift and abs(median - round(median / 60) * 60) <= 5
            supported = bool(mask.any() and not ambiguous and (correctable or drift))
            refs = tuple(f'{source}:{row}' for source, row in zip(f.loc[mask, '_source'], f.loc[mask, '_row']))
            candidates.append(Candidate(station, 'all', 'clock_error', 'drift' if drift else 'offset',
                part.logger.min(), part.logger.max(), refs,
                {'supported': supported, 'correctable': bool(correctable and supported), 'offset_seconds': round(median / 60) * 60,
                 'median_offset_seconds': median, 'mad_seconds': mad, 'valid_samples': len(part), 'threshold_seconds': 60,
                 'gps_rows': part.row.astype(int).tolist(), 'weather_rows': f.loc[mask, '_row'].astype(int).tolist(),
                 'scope_rows': f.loc[scope, '_row'].astype(int).tolist(),
                 'reason': 'GPS/logger displacement; subtract offset only within supported source rows' if correctable else 'GPS-supported drift; no constant correction is justified'}))
        lat, lon = float(g.lat.median()), float(g.lon.median())
        spread = float(np.percentile(distance_m(lat, lon, g.lat.to_numpy(), g.lon.to_numpy()), 95))
        mismatch = float(distance_m(pack.stations.loc[station, 'lat'], pack.stations.loc[station, 'lon'], lat, lon))
        if len(g) >= 24 and g.utc.max() - g.utc.min() >= pd.Timedelta(hours=24) and mismatch > 1000:
            candidates.append(Candidate(station, 'metadata', 'location_mismatch', 'coordinates', g.logger.min(), g.logger.max(),
                tuple(f'gps/{station}.nmea:{r}' for r in g.row),
                {'supported': spread <= 100, 'distance_m': round(mismatch, 1), 'spread95_m': round(spread, 1),
                 'valid_samples': len(g), 'threshold_m': 1000, 'reason': 'Verify installation coordinates against stable valid GPS fixes; weather values are not excluded'}))
    return candidates


def apply_supported_time_map(pack, candidates):
    result = replace(pack, weather={s: f.copy() for s, f in pack.weather.items()}, diagnostics=list(pack.diagnostics))
    for candidate in candidates:
        if candidate.issue != 'clock_error':
            continue
        f = result.weather[candidate.station_id]
        mask = f._row.isin(candidate.evidence['weather_rows'])
        scope = f._row.isin(candidate.evidence.get('scope_rows', candidate.evidence['weather_rows']))
        outside = scope & ~mask
        if outside.any():
            f.loc[outside, '_time'] = pd.NaT
            result.diagnostics.append({'station_id': candidate.station_id, 'check': 'clock_coverage',
                'rows': f.loc[outside, '_row'].astype(int).tolist(), 'reason': 'Clock-affected segment extends beyond GPS support; edge rows not corrected or used for timed comparisons'})
        if candidate.evidence.get('correctable'):
            f.loc[mask, '_time'] = f.loc[mask, '_logger_time'] - pd.Timedelta(seconds=candidate.evidence['offset_seconds'])
        else:
            f.loc[mask, '_time'] = pd.NaT
    return result
