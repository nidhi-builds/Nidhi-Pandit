"""Shared reference eligibility; suspect values never become corroborating evidence."""
import numpy as np
import pandas as pd
from .config import CHANNELS


def hourly_data(pack,candidates):
    hourly={}
    for station,original in pack.weather.items():
        frame=original.copy();keys=frame._source.str.cat(frame._row.astype(str),sep=':')
        for c in candidates:
            if c.station_id!=station:continue
            suspect=c.issue in ('missing_data','out_of_range','flatline','spike') or c.issue=='duplicate_data' and (c.subtype=='conflicting' or not c.evidence.get('supported'))
            if suspect:
                columns=list(CHANNELS) if c.channel=='all' else [c.channel]
                frame.loc[keys.isin(c.row_refs),columns]=np.nan
        frame=frame.loc[frame._time.notna()].drop_duplicates('_time',keep='first').set_index('_time')
        values=frame[list(CHANNELS)].resample('h').median()
        values['rain_mm']=frame.rain_mm.resample('h').sum(min_count=1)
        hourly[station]=values
    return hourly


def qualified_basic_peers(hourly,station,channel):
    target=hourly[station][channel];qualified=[]
    for other,frame in hourly.items():
        if other==station:continue
        paired=pd.concat([target,frame[channel]],axis=1,keys=['target','peer']).dropna()
        if len(paired)<168:continue
        span=(paired.index[-1]-paired.index[0]).total_seconds()/3600+1
        if span<168 or len(paired)/span<.7:continue
        changes=paired.diff();changes.loc[paired.index.to_series().diff().ne(pd.Timedelta(hours=1))]=np.nan
        correlation=changes.corr().iloc[0,1]
        threshold=.7 if channel=='pressure_hpa' else .3 if channel=='wind_kmh' else .5
        if np.isfinite(correlation) and correlation>=threshold:qualified.append(other)
    return qualified
