"""Small independent interval scorer; overlapping-fault tests use direct assertions."""
import pandas as pd
import numpy as np


def evaluate(predictions, truth, cadence_minutes):
    cadence=pd.Timedelta(minutes=cadence_minutes)
    pairs=[]
    for i,p in enumerate(predictions):
        for j,t in enumerate(truth):
            if any(p[k]!=t[k] for k in ('station_id','channel','issue','action')): continue
            start,end=max(pd.Timestamp(p['start']),pd.Timestamp(t['start'])),min(pd.Timestamp(p['end']),pd.Timestamp(t['end']))
            intersection=max(0.,(end-start)/cadence+1)
            union=(pd.Timestamp(p['end'])-pd.Timestamp(p['start']))/cadence+1+(pd.Timestamp(t['end'])-pd.Timestamp(t['start']))/cadence+1-intersection
            overlap=intersection/union if union else 0
            if overlap>=.5: pairs.append((-overlap,i,j))
    used_p,used_t=set(),set(); boundaries=[]
    for _,i,j in sorted(pairs):
        if i in used_p or j in used_t: continue
        used_p.add(i); used_t.add(j)
        boundaries.append(max(abs((pd.Timestamp(predictions[i]['start'])-pd.Timestamp(truth[j]['start'])).total_seconds()),abs((pd.Timestamp(predictions[i]['end'])-pd.Timestamp(truth[j]['end'])).total_seconds()))/60)
    tp=len(used_p); fp=len(predictions)-tp; fn=len(truth)-tp
    return {'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,'boundary_minutes':boundaries}


def candidate_rows(candidates):
    return [dict(station_id=c.station_id,channel=c.channel,issue=c.issue,subtype=c.subtype,start=c.start,end=c.end,action='exclude')
            for c in candidates if c.evidence.get('supported') and c.issue not in ('clock_error','location_mismatch','duplicate_data','corroborated_weather_event') and c.start is not None]


def good_data_loss(predictions, truth, frames):
    lost=good=0
    channels=['temp_c','rh_pct','pressure_hpa','wind_kmh','wind_dir_deg','rain_mm','ghi_wm2']
    for station,frame in frames.items():
        time=pd.to_datetime(frame.timestamp_utc)
        for channel in channels:
            bad=np.zeros(len(frame),dtype=bool); flagged=bad.copy()
            for events,mask in ((truth,bad),(predictions,flagged)):
                for event in events:
                    if event['station_id']==station and event['channel'] in (channel,'all'):
                        mask |= time.between(event['start'],event['end']).to_numpy()
            good+=int((~bad).sum());lost+=int((flagged & ~bad).sum())
    return lost,good
