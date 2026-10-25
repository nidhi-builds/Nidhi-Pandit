"""Independent weather/fault generator: deliberately imports no detector code."""
from pathlib import Path
import numpy as np
import pandas as pd

FAMILIES = ('flatline', 'spike', 'additive', 'multiplicative', 'gradual', 'conditional', 'rain')
CHANNELS = ['temp_c', 'rh_pct', 'pressure_hpa', 'wind_kmh', 'wind_dir_deg', 'rain_mm', 'ghi_wm2']


def scenario(root: Path, seed: int, family: str, control=False):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'data').mkdir(exist_ok=True)
    rng = np.random.default_rng(seed)
    cadence = (10, 20, 30)[seed % 3]
    days = 25
    time = pd.date_range('2023-08-01', periods=days * 1440 // cadence, freq=f'{cadence}min')
    hour = np.arange(len(time)) * cadence / 60
    phase = (seed % 7) / 10
    sun = np.maximum(0, np.sin(2 * np.pi * (hour % 24 - 12) / 24))
    regional = 2 * np.sin(hour / (19 + seed % 3) + phase) + np.cos(hour / 8 + phase)
    wind = 6 + np.sin(hour / 5 + phase) + .5 * np.sin(hour / 17)
    ids = [f'N{seed % 997}_{i}' for i in range(3 + seed % 2)]
    target = ids[seed % len(ids)]
    onset = pd.Timestamp('2023-08-01') + pd.Timedelta(days=9 + seed % 3)
    affected = np.zeros(len(time), dtype=bool)
    channel = {'flatline':'temp_c','spike':'temp_c','additive':('pressure_hpa','temp_c','rh_pct')[seed % 3],
               'multiplicative':'wind_kmh','gradual':'temp_c','conditional':'temp_c','rain':'rain_mm'}[family]
    issue = {'additive':'sensor_bias','multiplicative':'sensor_bias','gradual':'sensor_bias','conditional':'sensor_bias','rain':'rainfall_underresponse'}.get(family, family)
    frames, stations = {}, []
    for i, station in enumerate(ids):
        elevation = 1200 + 300 * i
        stations.append([station, f'Synthetic {station}', 39 + .03 * i, -104 + .02 * i, elevation, '2020-01-01', cadence])
        f = pd.DataFrame({'timestamp_utc': time.strftime('%Y-%m-%d %H:%M'),
            'temp_c': 15 - .006 * (elevation - 1200) + regional + (6 + i * .05) * sun + rng.normal(0,.06,len(time)),
            'rh_pct': 55 + 8 * np.cos(hour / 13 + phase) - 8 * sun + i + rng.normal(0,.08,len(time)),
            'pressure_hpa': 870 - i * 28 + 2 * regional + rng.normal(0,.03,len(time)),
            'wind_kmh': wind * (1 + i * .05) + rng.normal(0,.04,len(time)),
            'wind_dir_deg': (hour * 5 + 350) % 360,
            'rain_mm': np.zeros(len(time)), 'ghi_wm2': sun * (680 + i * 3)})
        if family == 'conditional' and station == target:
            f['wind_kmh'] = 3
        if family == 'rain':
            f['temp_c'] = 12
            for day in (2,5,12,15,18,21):
                mask = (time >= time[0] + pd.Timedelta(days=day)) & (time < time[0] + pd.Timedelta(days=day,hours=2))
                f.loc[mask, 'rain_mm'] = 2.4 / mask.sum()
        if station == target:
            if family == 'flatline':
                affected = (time >= onset) & (time < onset + pd.Timedelta(hours=36))
                if not control: f.loc[affected, channel] = 12.345
            elif family == 'spike':
                affected[len(time)//2 + seed % 17] = True
                if not control: f.loc[affected, channel] += 12 * (-1 if seed % 2 else 1)
            elif family in ('additive','multiplicative','gradual'):
                affected = time >= onset
                if not control:
                    if family == 'additive': f.loc[affected, channel] += {'temp_c':4,'pressure_hpa':6,'rh_pct':18}[channel]
                    elif family == 'multiplicative': f.loc[affected,channel] *= .5 if seed % 2 else 1.8
                    else: f.loc[affected,channel] += np.linspace(0,5,affected.sum())
            elif family == 'conditional':
                affected = (time >= onset) & f.ghi_wm2.ge(400).to_numpy()
                if not control: f.loc[affected,channel] += 4
            else:
                affected = (time >= onset) & f.rain_mm.gt(0).to_numpy()
                if not control: f.loc[affected,channel] = 0
        f.to_csv(root/'data'/f'{station}.csv',index=False,float_format='%.5f')
        frames[station] = f
    pd.DataFrame(stations,columns=['station_id','name','lat','lon','elevation_m','installed','logger_interval_min']).to_csv(root/'stations.csv',index=False)
    truth=[]
    selected=np.flatnonzero(affected)
    if len(selected) and not control:
        for run in np.split(selected,np.flatnonzero(np.diff(selected)>1)+1):
            truth.append({'station_id':target,'channel':channel,'issue':issue,'subtype':family,
                          'start':time[run[0]],'end':time[run[-1]],'action':'exclude','parent_episode':f'{seed}-{family}'})
    return truth, frames, cadence
