"""Synthetic inputs only; this module never imports checker code."""
from pathlib import Path
import numpy as np
import pandas as pd

CHANNELS = ['temp_c', 'rh_pct', 'pressure_hpa', 'wind_kmh', 'wind_dir_deg', 'rain_mm', 'ghi_wm2']


def make_pack(root: Path, days=2, cadence=10, ids=('A', 'B', 'C'), seed=11):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'data').mkdir(exist_ok=True)
    time = pd.date_range('2024-05-01', periods=int(days * 1440 / cadence), freq=f'{cadence}min')
    rng = np.random.default_rng(seed)
    hour = np.arange(len(time)) * cadence / 60
    sun = np.maximum(0, np.sin(2 * np.pi * (hour % 24 - 12) / 24))
    regional = 2 * np.sin(hour / 20) + np.sin(hour / 7)
    frames = {}
    stations = []
    for i, station in enumerate(ids):
        stations.append([station, f'School {station}', 40 + i * .02, -105 + i * .02,
                         1500 + 100 * i, '2023-01-01', cadence])
        frame = pd.DataFrame({
            'timestamp_utc': time.strftime('%Y-%m-%d %H:%M'),
            'temp_c': 12 - i * .6 + regional + 7 * sun + rng.normal(0, .05, len(time)),
            'rh_pct': 55 + i + 10 * np.cos(hour / 13) - 8 * sun + rng.normal(0, .1, len(time)),
            'pressure_hpa': 850 - 10 * i + regional * 2 + rng.normal(0, .03, len(time)),
            'wind_kmh': 5 + .7 * np.sin(hour / 3) + .8 * np.cos(hour / 11) + rng.normal(0, .05, len(time)),
            'wind_dir_deg': (hour * 3 + 350) % 360,
            'rain_mm': np.zeros(len(time)),
            'ghi_wm2': 700 * sun,
        })
        frame.to_csv(root / 'data' / f'{station}.csv', index=False, float_format='%.4f')
        frames[station] = frame
    pd.DataFrame(stations, columns=['station_id', 'name', 'lat', 'lon', 'elevation_m',
                                   'installed', 'logger_interval_min']).to_csv(root / 'stations.csv', index=False)
    return frames


def save(root, station, frame):
    frame.to_csv(root / 'data' / f'{station}.csv', index=False, float_format='%.4f')


def sentence(body):
    checksum = 0
    for char in body:
        checksum ^= ord(char)
    return f'${body}*{checksum:02X}'


def add_gps(root, station, times, offsets=None, lat='4000.0000', lon='10500.0000', valid=True):
    (root / 'gps').mkdir(exist_ok=True)
    offsets = np.zeros(len(times)) if offsets is None else offsets
    lines = []
    for time, offset in zip(times, offsets):
        timestamp = pd.Timestamp(time)
        logger = timestamp + pd.Timedelta(seconds=float(offset))
        body = f'GPRMC,{timestamp:%H%M%S}.00,{"A" if valid else "V"},{lat},N,{lon},W,0,0,{timestamp:%d%m%y},,,A'
        lines.append(f'{logger:%Y-%m-%d %H:%M:%S},{sentence(body)}')
    (root / 'gps' / f'{station}.nmea').write_text('\n'.join(lines), encoding='ascii')
