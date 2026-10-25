"""Strict input boundaries and deterministic, atomic serialization."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from dataclasses import asdict
import numpy as np
import pandas as pd
from .config import CHANNELS, FIELDS
from .types import Pack


def load_pack(folder: Path) -> Pack:
    folder = Path(folder).resolve()
    metadata = folder / 'stations.csv'
    if not metadata.is_file():
        raise ValueError('stations.csv is required')
    stations = pd.read_csv(metadata, dtype=str, keep_default_na=False)
    required = {'station_id', 'name', 'lat', 'lon', 'elevation_m', 'installed', 'logger_interval_min'}
    if not required.issubset(stations.columns) or stations.empty:
        raise ValueError('stations.csv has missing required columns or no stations')
    if stations.station_id.duplicated().any() or not stations.station_id.map(lambda s: bool(re.fullmatch(r'[A-Za-z0-9_-]+', s))).all():
        raise ValueError('station IDs must be unique safe file names')
    for column in ('lat', 'lon', 'elevation_m', 'logger_interval_min'):
        stations[column] = pd.to_numeric(stations[column], errors='coerce')
        if not np.isfinite(stations[column]).all():
            raise ValueError(f'invalid metadata {column}')
    if not stations.lat.between(-90, 90).all() or not stations.lon.between(-180, 180).all():
        raise ValueError('invalid latitude or longitude')
    if not (stations.logger_interval_min > 0).all():
        raise ValueError('logger interval must be positive')
    stations = stations.set_index('station_id').sort_index()
    files = [metadata]
    weather, gps, diagnostics = {}, {}, []
    for station in stations.index:
        path = folder / 'data' / f'{station}.csv'
        if not path.is_file():
            raise ValueError(f'missing data/{station}.csv')
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if not {'timestamp_utc', *CHANNELS}.issubset(frame.columns):
            raise ValueError(f'data/{station}.csv has missing required columns')
        frame['_raw_time'] = frame.timestamp_utc
        frame['_logger_time'] = pd.to_datetime(frame.timestamp_utc, format='%Y-%m-%d %H:%M', errors='coerce')
        frame['_time'] = frame['_logger_time']
        frame['_source'] = f'data/{station}.csv'
        frame['_row'] = np.arange(2, len(frame) + 2)
        frame['_segment'] = frame['_time'].diff().lt(pd.Timedelta(0)).cumsum()
        for channel in CHANNELS:
            frame[channel] = pd.to_numeric(frame[channel], errors='coerce').replace([np.inf, -np.inf], np.nan)
        weather[station] = frame
        files.append(path)
        path = folder / 'gps' / f'{station}.nmea'
        if path.is_file():
            files.append(path)
            gps[station] = path.read_text(encoding='utf-8', errors='replace').splitlines()
        else:
            gps[station] = []
            diagnostics.append({'station_id': station, 'check': 'gps', 'reason': 'GPS absent; time/location corroboration unavailable'})
    notes = folder / 'maintenance_log.md'
    if notes.is_file():
        files.append(notes)
    else:
        diagnostics.append({'check': 'maintenance', 'reason': 'Maintenance notes absent'})
    if (folder / 'README.md').is_file():
        files.append(folder / 'README.md')
    hashes = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    return Pack(stations, weather, gps, notes.read_text(encoding='utf-8', errors='replace') if notes.is_file() else '', hashes, diagnostics)


def fingerprint(hashes: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def atomic_write(path: Path, content: str) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def csv_text(rows, fields=FIELDS):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def write_outputs(result, html: str, output_dir: Path):
    review_fields=('station_id','channel','start_utc','end_utc','candidate_issue','reason','needed_evidence')
    outputs={'flags.csv':csv_text([asdict(f) for f in result.flags]),
             'review.csv':csv_text(result.reviews,review_fields),
             'evidence.json':json.dumps(result.evidence,sort_keys=True,indent=2,allow_nan=False,default=str)+'\n',
             'report.html':html}
    # Serialize everything before replacing any existing result.
    for name,content in outputs.items(): atomic_write(output_dir/name,content)
