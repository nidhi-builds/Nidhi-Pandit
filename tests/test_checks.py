import pandas as pd
import pytest
from tests.helpers import make_pack, save
from ridgeline.io import load_pack
from ridgeline.checks import check_basic


def test_gaps_duplicates_conflicts_and_missing_values(tmp_path):
    frames = make_pack(tmp_path, ids=('A',), cadence=30)
    f = frames['A'].drop(index=[5, 6]).copy()
    f.loc[9, 'temp_c'] = float('nan')
    copy = f.iloc[[10]].copy()
    conflict = f.iloc[[12]].copy()
    conflict['rh_pct'] += 5
    f = pd.concat([f, copy, conflict], ignore_index=True)
    save(tmp_path, 'A', f)
    candidates = check_basic(load_pack(tmp_path))
    gaps = [c for c in candidates if c.subtype == 'records']
    assert len(gaps) == 1
    assert gaps[0].start == pd.Timestamp('2024-05-01 02:30')
    assert gaps[0].end == pd.Timestamp('2024-05-01 03:00')
    assert any(c.subtype == 'identical' for c in candidates)
    assert any(c.subtype == 'conflicting' and c.channel == 'rh_pct' for c in candidates)
    assert any(c.issue == 'missing_data' and c.channel == 'temp_c' for c in candidates)


def test_empty_edges_are_not_invented_gaps_and_reset_not_deduplicated(tmp_path):
    frames = make_pack(tmp_path, ids=('A',))
    f = frames['A'].iloc[12:-12].copy()
    f.loc[f.index >= 144, 'timestamp_utc'] = (pd.to_datetime(f.loc[f.index >= 144, 'timestamp_utc']) - pd.Timedelta(hours=1)).dt.strftime('%Y-%m-%d %H:%M')
    save(tmp_path, 'A', f)
    candidates = check_basic(load_pack(tmp_path))
    assert not any(c.subtype == 'records' for c in candidates)
    duplicates = [c for c in candidates if c.issue == 'duplicate_data']
    assert all(not c.evidence['supported'] for c in duplicates)


def test_hard_ranges_spike_and_supported_flatline(tmp_path):
    frames = make_pack(tmp_path, days=12)
    frames['A'].loc[10, 'rh_pct'] = 101
    frames['A'].loc[11, 'rain_mm'] = -.2
    frames['A'].loc[12, 'wind_kmh'] = -1
    frames['A'].loc[13, 'wind_dir_deg'] = 361
    frames['A'].loc[100, 'temp_c'] += 15
    frames['A'].loc[288:575, 'pressure_hpa'] = 850
    save(tmp_path, 'A', frames['A'])
    candidates = check_basic(load_pack(tmp_path))
    assert len([c for c in candidates if c.issue == 'out_of_range']) == 4
    assert any(c.issue == 'spike' and c.channel == 'temp_c' and c.evidence['supported'] for c in candidates)
    assert any(c.issue == 'flatline' and c.channel == 'pressure_hpa' and c.evidence['supported'] for c in candidates)


def test_saturation_dryness_darkness_and_calm_are_not_excluded(tmp_path):
    frames = make_pack(tmp_path, days=3)
    for station, frame in frames.items():
        frame['rh_pct'] = 100
        frame['ghi_wm2'] = 0
        frame['wind_kmh'] = 0
        frame['wind_dir_deg'] = 360
        save(tmp_path, station, frame)
    candidates = check_basic(load_pack(tmp_path))
    assert not any(c.issue in ('out_of_range', 'flatline', 'spike') and c.evidence['supported'] for c in candidates)


def test_unverified_clock_collision_is_not_confirmed_conflict(tmp_path):
    frames=make_pack(tmp_path,ids=('A',))
    f=frames['A'];extra=f.iloc[[10]].copy();extra['temp_c']+=2
    save(tmp_path,'A',pd.concat([f,extra],ignore_index=True))
    pack=load_pack(tmp_path);pack.weather['A'].loc[len(f),'_time']=pd.NaT
    duplicates=[c for c in check_basic(pack) if c.issue=='duplicate_data']
    assert duplicates and all(not c.evidence['supported'] for c in duplicates)


def test_recovery_from_stuck_sensor_is_not_an_isolated_spike(tmp_path):
    frames=make_pack(tmp_path,days=12);f=frames['A']
    f.loc[:299,'temp_c']=6.5
    f.loc[300:304,'temp_c']=[.9,1.6,2.3,2.9,3.5]
    save(tmp_path,'A',f)
    candidates=check_basic(load_pack(tmp_path))
    recovery=pd.Timestamp(f.loc[300,'timestamp_utc'])
    assert not any(c.issue=='spike' and c.start==recovery and c.evidence['supported'] for c in candidates)


def test_two_record_spike_is_one_event_with_return(tmp_path):
    frames=make_pack(tmp_path,days=12)
    frames['A'].loc[200:201,'temp_c']+=12;save(tmp_path,'A',frames['A'])
    spikes=[c for c in check_basic(load_pack(tmp_path)) if c.station_id=='A' and c.issue=='spike' and c.evidence['supported']]
    assert len(spikes)==1 and len(spikes[0].row_refs)==2


def test_large_spike_with_background_trend_still_has_a_return(tmp_path):
    import numpy as np
    frames=make_pack(tmp_path,days=12);f=frames['A']
    f.loc[1197:1204,'temp_c']+=np.linspace(-2,2,8)
    f.loc[1200,'temp_c']+=70;save(tmp_path,'A',f)
    event=pd.Timestamp(f.loc[1200,'timestamp_utc'])
    assert any(c.issue=='spike' and c.start==event and c.evidence['supported'] for c in check_basic(load_pack(tmp_path)))


@pytest.mark.parametrize('cadence',[5,10,30])
@pytest.mark.parametrize('missing',[1,6,144])
def test_structural_gap_counts_and_boundaries_across_cadences(tmp_path,cadence,missing):
    frames=make_pack(tmp_path,days=6,cadence=cadence,ids=('A',));f=frames['A']
    start=pd.Timestamp(f.loc[12,'timestamp_utc']);end=pd.Timestamp(f.loc[12+missing-1,'timestamp_utc'])
    save(tmp_path,'A',f.drop(index=range(12,12+missing)))
    gaps=[c for c in check_basic(load_pack(tmp_path)) if c.subtype=='records']
    assert len(gaps)==1 and gaps[0].start==start and gaps[0].end==end
    assert gaps[0].evidence['missing_records']==missing
