import pandas as pd
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
