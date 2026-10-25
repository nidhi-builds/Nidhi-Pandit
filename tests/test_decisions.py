from pathlib import Path
from dataclasses import asdict
import pandas as pd
from tests.helpers import make_pack, save
from ridgeline.io import load_pack, write_outputs
from ridgeline.checks import check_basic, row_refs
from ridgeline.types import Candidate
from ridgeline.decisions import decide


def test_duplicate_merge_and_metadata_never_excludes_weather(tmp_path):
    frames=make_pack(tmp_path,ids=('A',))
    save(tmp_path,'A',pd.concat([frames['A'],frames['A'].iloc[10:12]],ignore_index=True))
    pack=load_pack(tmp_path);basic=check_basic(pack)
    metadata=Candidate('A','metadata','location_mismatch','coordinates',pd.Timestamp('2024-05-01'),pd.Timestamp('2024-05-02'),(),{'supported':True,'distance_m':2000,'reason':'Stable GPS mismatch'})
    result=decide(pack,basic+[metadata])
    duplicate=[f for f in result.flags if f.issue=='duplicate_data']
    assert len(duplicate)==1 and duplicate[0].action=='correct'
    assert 'remove' in duplicate[0].note.lower() and 'rows' in duplicate[0].note
    assert any(f.channel=='metadata' and f.action=='exclude' for f in result.flags)
    assert result.summary['stations'][0]['channels']['temp_c']['exclude']==0
    assert result.summary['stations'][0]['duplicate_copies']==2


def test_precedence_uncertainty_and_evidence(tmp_path):
    make_pack(tmp_path,ids=('A',));pack=load_pack(tmp_path);part=pack.weather['A'].iloc[10:20]
    args=('A','temp_c','flatline','constant',part._logger_time.min(),part._logger_time.max(),row_refs(part))
    high=Candidate(*args,{'supported':True,'constant_value':6.5,'reason':'Exact constant sensor'})
    low=Candidate('A','temp_c','sensor_bias','additive',high.start,high.end,high.row_refs,{'supported':True,'departure':3,'reason':'Generic bias'})
    uncertain=Candidate('A','rain_mm','rainfall_underresponse','episodes',high.start,high.end,high.row_refs,{'supported':False,'reason':'Could be local rain'})
    result=decide(pack,[low,high,uncertain])
    assert [f.issue for f in result.flags]==['flatline']
    assert len(result.reviews)==1 and result.reviews[0]['candidate_issue']=='rainfall_underresponse'
    assert result.evidence['flags'][0]['source_rows']==list(high.row_refs)
    assert result.evidence['flags'][0]['rule_version']
    assert result.evidence['flags'][0]['quantities']['samples']==10
    assert 'data/A.csv' in result.flags[0].note


def test_disjoint_counts_and_clock_instruction(tmp_path):
    make_pack(tmp_path,ids=('A',));pack=load_pack(tmp_path);part=pack.weather['A'].iloc[0:5]
    clock=Candidate('A','all','clock_error','offset',part._logger_time.min(),part._logger_time.max(),row_refs(part),{'supported':True,'correctable':True,'offset_seconds':-21600,'weather_rows':part._row.tolist(),'reason':'GPS agrees'})
    fault=Candidate('A','temp_c','out_of_range','domain',clock.start,clock.end,clock.row_refs,{'supported':True,'reason':'Invalid'})
    result=decide(pack,[clock,fault])
    assert 'add 360 minutes' in next(f.note for f in result.flags if f.issue=='clock_error')
    counts=result.summary['stations'][0]['channels']['temp_c']
    assert counts['exclude']==5 and counts['correct']==0
    assert sum(counts[k] for k in ('exclude','correct','review','screened'))==counts['total_observed']


def test_outputs_schema_and_byte_determinism(tmp_path):
    make_pack(tmp_path/'pack',ids=('A',));pack=load_pack(tmp_path/'pack')
    result=decide(pack,check_basic(pack));out=tmp_path/'out';out.mkdir()
    write_outputs(result,'<html>test</html>',out)
    first={p.name:p.read_bytes() for p in out.iterdir()}
    for _ in range(2): write_outputs(decide(pack,check_basic(pack)),'<html>test</html>',out)
    assert all((out/name).read_bytes()==content for name,content in first.items())
    assert pd.read_csv(out/'flags.csv').columns.tolist()==['station_id','channel','start_utc','end_utc','issue','action','note']


def test_keep_requires_positive_evidence_and_cannot_hide_fault(tmp_path):
    make_pack(tmp_path);pack=load_pack(tmp_path);part=pack.weather['A'].iloc[0:5]
    keep=Candidate('A','temp_c','corroborated_weather_event','regional',part._logger_time.min(),part._logger_time.max(),row_refs(part),{'supported':True,'references':['B','C'],'reason':'Coherent regional event'})
    assert decide(pack,[keep]).flags[0].action=='keep'
    fault=Candidate('A','temp_c','out_of_range','domain',keep.start,keep.end,keep.row_refs,{'supported':True,'reason':'Invalid'})
    result=decide(pack,[keep,fault])
    assert not any(f.action=='keep' for f in result.flags)
    clock=Candidate('A','all','clock_error','drift',keep.start,keep.end,keep.row_refs,{'supported':True,'correctable':False,'reason':'Time is unreliable'})
    assert not any(f.action=='keep' for f in decide(pack,[keep,clock]).flags)


def test_disjoint_clock_edges_are_not_one_long_review_interval(tmp_path):
    make_pack(tmp_path,ids=('A',));pack=load_pack(tmp_path)
    pack.diagnostics.append({'station_id':'A','check':'clock_coverage','rows':[2,3,288,289],'reason':'Outside GPS support'})
    result=decide(pack,[])
    assert len(result.reviews)==2
    assert all(pd.Timestamp(r['end_utc'])-pd.Timestamp(r['start_utc'])<=pd.Timedelta(minutes=10) for r in result.reviews)
