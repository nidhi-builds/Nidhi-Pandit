"""Final actions and short explanations derive from measured evidence only."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .checks import intervals
from .config import CHANNELS, VERSION
from .io import fingerprint
from .types import Flag, RunResult

ISSUES = {'missing_data','duplicate_data','clock_error','location_mismatch','out_of_range','flatline','spike','sensor_bias','rainfall_underresponse','corroborated_weather_event'}
PRIORITY = {'out_of_range':100,'missing_data':95,'flatline':90,'spike':80,'sensor_bias':70,'rainfall_underresponse':60}


def stamp(value):
    return '' if value is None or pd.isna(value) else pd.Timestamp(value).strftime('%Y-%m-%d %H:%M')


def ranges(numbers):
    numbers=sorted(set(int(n) for n in numbers))
    if not numbers: return ''
    groups=np.split(numbers,np.flatnonzero(np.diff(numbers)>1)+1)
    return ','.join(str(g[0]) if len(g)==1 else f'{g[0]}-{g[-1]}' for g in groups)


def sources(refs):
    files={}
    for ref in refs:
        name,row=ref.rsplit(':',1);files.setdefault(name,[]).append(int(row))
    return '; '.join(f'{name} rows {ranges(rows)}' for name,rows in sorted(files.items()))


def review(candidate, reason=None):
    return dict(station_id=candidate.station_id,channel=candidate.channel,start_utc=stamp(candidate.start),end_utc=stamp(candidate.end),
                candidate_issue=candidate.issue,reason=reason or candidate.evidence.get('reason','Insufficient independent evidence'),
                needed_evidence='Verify source records, time and an independent reference before choosing an action')


def action_for(c):
    if c.issue=='corroborated_weather_event': return 'keep'
    if c.issue=='duplicate_data' and c.subtype=='identical': return 'correct'
    if c.issue=='clock_error' and c.evidence.get('correctable'): return 'correct'
    return 'exclude'


def note_for(c,action,quantities):
    evidence=c.evidence
    detail=evidence.get('reason',c.issue.replace('_',' ')).rstrip('.')
    if c.issue=='clock_error' and action=='correct':
        minutes=-evidence['offset_seconds']/60
        detail=f'GPS supports {"add" if minutes>=0 else "subtract"} {abs(minutes):g} minutes to logger labels within the specified source rows only'
    elif c.issue=='duplicate_data' and action=='correct':
        detail=f'Retain first occurrence of each logger timestamp and remove verified identical copies at rows {ranges(evidence.get("remove_rows",[]))}'
    elif c.issue=='location_mismatch':
        detail=f'Withhold installation coordinates pending verification; GPS mismatch {evidence.get("distance_m",0):g} m; weather values remain eligible for their own checks'
    elif 'departure' in evidence:
        detail+=f'; measured departure {evidence["departure"]:g}'
    if 'constant_value' in evidence:
        detail+=f'; constant value {evidence["constant_value"]:g}'
    if 'observed_min' in quantities and c.issue in ('out_of_range','spike'):
        detail+=f'; observed {quantities["observed_min"]:g} to {quantities["observed_max"]:g}'
    references=evidence.get('references',[])
    if references: detail+='; references '+','.join(references)
    detail+='; '+evidence.get('time_basis','original logger UTC labels')
    if c.row_refs: detail+='; '+sources(c.row_refs)
    return detail+'.'


def decide(pack,candidates):
    accepted=[];reviews=[];occupied={}; source_keys={s:f._source.str.cat(f._row.astype(str),sep=':') for s,f in pack.weather.items()}
    for c in sorted(deepcopy(candidates),key=lambda c:(-PRIORITY.get(c.issue,0),c.station_id,c.channel,stamp(c.start),c.subtype)):
        if c.issue not in ISSUES or c.channel not in (*CHANNELS,'all','metadata'):
            raise ValueError('Invalid internal issue or channel')
        if not c.evidence.get('supported') or not stamp(c.start) or not stamp(c.end):
            reviews.append(review(c));continue
        if c.start>c.end: raise ValueError('Reversed flag interval')
        action=action_for(c)
        covered=occupied.setdefault((c.station_id,c.channel),set())
        if c.issue=='corroborated_weather_event':
            if len(set(c.evidence.get('references',[])) & set(pack.weather))<2 or set(c.row_refs)&(covered|occupied.get((c.station_id,'all'),set())):
                reviews.append(review(c,'Keep is not supported independently of conflicting faults'));continue
        parts=[c]
        if action=='exclude' and c.channel=='all': covered.update(c.row_refs)
        if action=='exclude' and c.row_refs and c.channel in CHANNELS:
            remaining=set(c.row_refs)-covered
            parts=intervals(pack,c.station_id,c.channel,c.issue,c.subtype,source_keys[c.station_id].isin(remaining),c.evidence)
            covered.update(remaining)
        accepted.extend((p,action) for p in parts)
    accepted.sort(key=lambda item:(item[0].station_id,item[0].channel,item[0].issue,item[1],item[0].subtype,stamp(item[0].start)))
    merged=[]
    for c,action in accepted:
        if merged:
            previous,old_action=merged[-1]
            same=(previous.station_id,previous.channel,previous.issue,previous.subtype,old_action)==(c.station_id,c.channel,c.issue,c.subtype,action)
            frame=pack.weather[c.station_id]
            same_segments=set(frame.loc[source_keys[c.station_id].isin(previous.row_refs),'_segment'])==set(frame.loc[source_keys[c.station_id].isin(c.row_refs),'_segment'])
            cadence=pd.Timedelta(minutes=pack.stations.loc[c.station_id,'logger_interval_min'])
            if same and same_segments and pd.Timedelta(0)<=c.start-previous.end<=cadence and c.issue!='clock_error':
                previous.end=max(previous.end,c.end)
                previous.row_refs=tuple(sorted(set(previous.row_refs+c.row_refs),key=lambda r:(r.rsplit(':',1)[0],int(r.rsplit(':',1)[1]))))
                if c.issue=='duplicate_data':
                    previous.evidence['remove_rows']=sorted(set(previous.evidence.get('remove_rows',[])+c.evidence.get('remove_rows',[])))
                previous.evidence['component_count']=previous.evidence.get('component_count',1)+1
                continue
        merged.append((c,action))
    merged.sort(key=lambda item:(item[0].station_id,stamp(item[0].start),item[0].channel,item[0].issue,item[1]))
    flags=[];entries=[]
    for c,action in merged:
        f=pack.weather[c.station_id];selected=f.loc[source_keys[c.station_id].isin(c.row_refs)]
        quantities={'samples':len(c.row_refs)}
        if c.channel in CHANNELS and len(selected) and selected[c.channel].notna().any():
            quantities.update(observed_min=float(selected[c.channel].min()),observed_max=float(selected[c.channel].max()))
        flags.append(Flag(c.station_id,c.channel,stamp(c.start),stamp(c.end),c.issue,action,note_for(c,action,quantities)))
        entries.append({'flag_row':len(flags),'flag':asdict(flags[-1]),'subtype':c.subtype,'source_rows':list(c.row_refs),
                        'rule_version':VERSION,'quantities':quantities,'evidence':c.evidence,
                        'time_basis':c.evidence.get('time_basis','original logger UTC labels'),
                        'limitations':'Evidence-based screening; no laboratory calibration or authoritative truth supplied'})
    for d in pack.diagnostics:
        if d.get('check')=='clock_coverage':
            f=pack.weather[d['station_id']];part=f.loc[f._row.isin(d['rows'])]
            reviews.append(dict(station_id=d['station_id'],channel='all',start_utc=stamp(part._logger_time.min()),end_utc=stamp(part._logger_time.max()),
                candidate_issue='clock_error',reason=d['reason']+'; source rows '+ranges(d['rows']),needed_evidence='Additional valid GPS anchors'))
    rules=hashlib.sha256(b''.join((Path(__file__).parent/name).read_bytes() for name in ('config.py','io.py','gps.py','checks.py','relationships.py','decisions.py'))).hexdigest()
    summary=summarize(pack,merged,reviews)
    evidence={'rule_version':VERSION,'rule_fingerprint':rules,'input_fingerprint':fingerprint(pack.input_hashes),
              'input_hashes':pack.input_hashes,'flags':entries,'diagnostics':pack.diagnostics,'summary':summary}
    return RunResult(flags,sorted(reviews,key=lambda r:(r['station_id'],r['start_utc'],r['channel'],r['candidate_issue'])),evidence,summary)


def summarize(pack,accepted,reviews):
    stations=[]
    for station,f in pack.weather.items():
        keys=f._source.str.cat(f._row.astype(str),sep=':')
        redundant=set()
        for c,action in accepted:
            if c.station_id==station and c.issue=='duplicate_data' and action=='correct':redundant.update(c.evidence.get('remove_rows',[]))
        observed=~f._row.isin(redundant)
        state=pd.DataFrame('screened',index=f.index,columns=CHANNELS)
        for c,action in accepted:
            if c.station_id!=station or c.channel=='metadata' or c.issue=='duplicate_data' and action=='correct':continue
            mask=keys.isin(c.row_refs)
            columns=list(CHANNELS) if c.channel=='all' else [c.channel]
            if action=='correct':state.loc[mask,columns]='correct'
        for r in reviews:
            if r['station_id']!=station or r['channel']=='metadata' or not r['start_utc'] or not r['end_utc']:continue
            mask=f._logger_time.between(r['start_utc'],r['end_utc'])
            columns=list(CHANNELS) if r['channel']=='all' else [r['channel']]
            state.loc[mask,columns]=state.loc[mask,columns].where(state.loc[mask,columns]!='screened','review')
        for c,action in accepted:
            if c.station_id==station and action=='exclude' and c.channel!='metadata':
                columns=list(CHANNELS) if c.channel=='all' else [c.channel]
                state.loc[keys.isin(c.row_refs),columns]='exclude'
        channel_counts={}
        for channel in CHANNELS:
            counts=state.loc[observed,channel].value_counts()
            channel_counts[channel]={k:int(counts.get(k,0)) for k in ('screened','exclude','correct','review')}
            channel_counts[channel]['total_observed']=int(observed.sum())
            channel_counts[channel]['limited_comparison']=any(d.get('station_id')==station and d.get('channel')==channel and d.get('check')=='relationships' for d in pack.diagnostics)
        stations.append({'station_id':station,'name':str(pack.stations.loc[station,'name']),'channels':channel_counts,
            'duplicate_copies':len(redundant),'missing_records':sum(int(c.evidence.get('missing_records',0)) for c,a in accepted if c.station_id==station and c.subtype=='records'),
            'metadata_review':any(c.station_id==station and c.channel=='metadata' for c,a in accepted)})
    times=pd.concat([f._logger_time for f in pack.weather.values()]).dropna()
    return {'stations':stations,'start_utc':stamp(times.min()) if len(times) else '', 'end_utc':stamp(times.max()) if len(times) else '',
            'review_events':len(reviews),'meaning':'Screened means no supported fault found by completed checks; it does not certify climate quality'}
