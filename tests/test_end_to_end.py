from pathlib import Path
import json
import subprocess
import sys
import pandas as pd
from checker import investigate
from tests.helpers import make_pack,save
from tests.metrics import evaluate,good_data_loss


def test_scorer_known_counts_wrong_actions_and_overreach():
    t=dict(station_id='A',channel='temp_c',issue='spike',action='exclude',start='2024-01-01 00:00',end='2024-01-01 00:10')
    assert evaluate([t],[t],10)['precision']==1
    score=evaluate([t,t],[t],10)
    assert (score['tp'],score['fp'],score['fn'])==(1,1,0) and score['precision']==.5
    wrong=dict(t,action='keep')
    assert evaluate([wrong],[t],10)['recall']==0
    assert evaluate([dict(t,end='2024-01-02 00:00')],[t],10)['tp']==0
    assert evaluate([],[],10)['precision'] is None


def test_station_renaming_and_directory_order_do_not_change_flags(tmp_path):
    frames=make_pack(tmp_path/'one',days=18)
    frames['A'].loc[10*144:,'pressure_hpa']+=6;save(tmp_path/'one','A',frames['A'])
    first=investigate(tmp_path/'one')
    two=tmp_path/'two';(two/'data').mkdir(parents=True)
    mapping={'A':'Peak','B':'Plain','C':'Ridge'}
    meta=pd.read_csv(tmp_path/'one/stations.csv');meta['station_id']=meta.station_id.map(mapping);meta.iloc[::-1].to_csv(two/'stations.csv',index=False)
    for old,new in reversed(list(mapping.items())):(two/'data'/f'{new}.csv').write_bytes((tmp_path/'one/data'/f'{old}.csv').read_bytes())
    second=investigate(two);reverse={v:k for k,v in mapping.items()}
    core=lambda flags,rename:sorted((rename.get(f.station_id,f.station_id),f.channel,f.start_utc,f.end_utc,f.issue,f.action) for f in flags)
    assert core(first.flags,{})==core(second.flags,reverse)


def test_cli_is_offline_reproducible_and_preserves_input(tmp_path):
    source=tmp_path/'pack';make_pack(source,days=1,ids=('Q',))
    before={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
    output=tmp_path/'elsewhere';output.mkdir()
    # In-process network guard verifies the engine never needs a socket.
    import socket
    original=socket.socket
    def denied(*args,**kwargs):raise AssertionError('network access is forbidden')
    socket.socket=denied
    try:investigate(source)
    finally:socket.socket=original
    command=[sys.executable,str(Path('checker.py').resolve()),str(source)]
    snapshots=[]
    for _ in range(3):
        result=subprocess.run(command,cwd=output,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        snapshots.append({name:(output/name).read_bytes() for name in ('flags.csv','review.csv','evidence.json','report.html')})
    assert snapshots[0]==snapshots[1]==snapshots[2]
    assert all((source/name).read_bytes()==value for name,value in before.items())
    assert 'pending' in snapshots[0]['report.html'].decode().lower()


def test_one_corrupted_reference_does_not_condemn_healthy_stations(tmp_path):
    frames=make_pack(tmp_path,days=20,ids=('A','B','C','D'))
    frames['D'].loc[10*144:,'pressure_hpa']+=7;save(tmp_path,'D',frames['D'])
    result=investigate(tmp_path)
    faults=[f for f in result.flags if f.issue=='sensor_bias']
    assert faults and all(f.station_id=='D' for f in faults)


def test_finite_bias_stops_at_supported_recovery(tmp_path):
    frames=make_pack(tmp_path,days=25)
    frames['A'].loc[10*144:15*144-1,'pressure_hpa']+=6;save(tmp_path,'A',frames['A'])
    flags=[f for f in investigate(tmp_path).flags if f.issue=='sensor_bias' and f.station_id=='A']
    assert len(flags)==1 and flags[0].start_utc=='2024-05-11 00:00' and flags[0].end_utc=='2024-05-15 23:50'
