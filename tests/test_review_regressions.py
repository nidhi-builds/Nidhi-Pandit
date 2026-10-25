import numpy as np
import pandas as pd
from tests.helpers import make_pack,save,add_gps
from ridgeline.io import load_pack
from ridgeline.gps import audit_gps
from ridgeline.checks import check_basic
from ridgeline.relationships import hourly_data
from ridgeline.decisions import decide


def test_one_gps_run_cannot_correct_two_competing_weather_segments(tmp_path):
    frames=make_pack(tmp_path,days=1,ids=('A',))
    f=frames['A'].iloc[12:48].copy()
    save(tmp_path,'A',pd.concat([f,f],ignore_index=True))
    add_gps(tmp_path,'A',pd.date_range('2024-05-01',periods=6,freq='h'),np.full(6,7200))
    candidates=audit_gps(load_pack(tmp_path))
    assert candidates and not any(c.evidence.get('correctable') for c in candidates)


def test_constant_values_do_not_authorize_deletion_after_clock_reset(tmp_path):
    frames=make_pack(tmp_path,days=1,ids=('A',))
    f=frames['A'].iloc[:2].copy();save(tmp_path,'A',pd.concat([f,f.iloc[[0]]],ignore_index=True))
    candidates=check_basic(load_pack(tmp_path))
    duplicates=[c for c in candidates if c.issue=='duplicate_data']
    assert duplicates and all(not c.evidence['supported'] for c in duplicates)


def test_conflicting_duplicates_cannot_supply_reference_values(tmp_path):
    frames=make_pack(tmp_path,days=1,ids=('A',))
    f=frames['A'].iloc[:1].copy();other=f.copy();other['temp_c']=99
    save(tmp_path,'A',pd.concat([f,other],ignore_index=True))
    pack=load_pack(tmp_path);basic=check_basic(pack)
    assert any(c.subtype=='conflicting' and c.evidence['supported'] for c in basic)
    assert hourly_data(pack,basic)['A'].temp_c.isna().all()


def test_unplaceable_row_is_reviewed_by_identity_with_source_reference(tmp_path):
    frames=make_pack(tmp_path,days=1,ids=('A',));f=frames['A'].iloc[:2].copy()
    f.loc[0,'timestamp_utc']='broken';save(tmp_path,'A',f)
    pack=load_pack(tmp_path);result=decide(pack,check_basic(pack))
    assert result.summary['stations'][0]['channels']['temp_c']['review']==1
    assert 'data/A.csv' in result.reviews[0]['reason'] and 'rows 2' in result.reviews[0]['reason']
    assert result.evidence['reviews'][0]['source_rows']==['data/A.csv:2']


def test_two_failed_constant_references_cannot_confirm_a_spike(tmp_path):
    frames=make_pack(tmp_path,days=12)
    frames['A'].loc[1200,'temp_c']+=12
    for station in ('B','C'):frames[station]['temp_c']=20
    for station,f in frames.items():save(tmp_path,station,f)
    candidates=check_basic(load_pack(tmp_path))
    assert not any(c.station_id=='A' and c.issue=='spike' and c.evidence['supported'] for c in candidates)


def test_varied_replay_block_needs_independent_valid_gps_dates(tmp_path):
    frames=make_pack(tmp_path,days=3,ids=('A',));f=frames['A']
    save(tmp_path,'A',pd.concat([f,f.iloc[:144]],ignore_index=True))
    add_gps(tmp_path,'A',pd.date_range('2024-05-01',periods=72,freq='h'))
    pack=load_pack(tmp_path);candidates=check_basic(pack)
    duplicates=[c for c in candidates if c.issue=='duplicate_data']
    assert len(duplicates)==144 and all(c.evidence['supported'] and c.evidence['gps_supported_replay'] for c in duplicates)
    result=decide(pack,candidates)
    assert result.summary['stations'][0]['duplicate_copies']==144
