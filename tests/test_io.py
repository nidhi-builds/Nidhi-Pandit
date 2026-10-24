from pathlib import Path
import hashlib
import subprocess
import sys
import pandas as pd
import pytest
from tests.helpers import make_pack, save
from ridgeline.io import load_pack


def test_load_preserves_provenance_and_dynamic_cadence(tmp_path):
    frames = make_pack(tmp_path / 'input space', cadence=30, ids=('Hill_9',))
    pack = load_pack(tmp_path / 'input space')
    assert list(pack.weather) == ['Hill_9']
    assert pack.stations.loc['Hill_9', 'logger_interval_min'] == 30
    assert pack.weather['Hill_9']['_row'].tolist() == list(range(2, len(frames['Hill_9']) + 2))
    assert pack.weather['Hill_9']['_raw_time'].iloc[0] == '2024-05-01 00:00'
    assert pack.input_hashes['stations.csv'] == hashlib.sha256((tmp_path / 'input space/stations.csv').read_bytes()).hexdigest()
    assert pack.diagnostics  # absent optional context is disclosed


def test_bad_numeric_and_unplaceable_time_remain_visible(tmp_path):
    frames = make_pack(tmp_path, ids=('X',))
    frames['X']['temp_c'] = frames['X']['temp_c'].astype(object)
    frames['X'].loc[0, 'temp_c'] = 'broken'
    frames['X'].loc[1, 'timestamp_utc'] = 'not a timestamp'
    save(tmp_path, 'X', frames['X'])
    pack = load_pack(tmp_path)
    assert pd.isna(pack.weather['X'].loc[0, 'temp_c'])
    assert pd.isna(pack.weather['X'].loc[1, '_time'])
    assert len(pack.weather['X']) == len(frames['X'])


@pytest.mark.parametrize('change', ['schema', 'missing_file', 'bad_cadence', 'unsafe_id'])
def test_invalid_required_input_rejected(tmp_path, change):
    make_pack(tmp_path, ids=('X',))
    if change == 'schema':
        (tmp_path / 'data/X.csv').write_text('timestamp_utc,temp_c\n2024-01-01 00:00,5\n')
    elif change == 'missing_file':
        (tmp_path / 'data/X.csv').unlink()
    else:
        meta = pd.read_csv(tmp_path / 'stations.csv')
        meta.loc[0, 'logger_interval_min' if change == 'bad_cadence' else 'station_id'] = 0 if change == 'bad_cadence' else '../escape'
        meta.to_csv(tmp_path / 'stations.csv', index=False)
    with pytest.raises(ValueError):
        load_pack(tmp_path)


def test_cli_output_location_preservation_and_failure(tmp_path):
    source = tmp_path / 'source'
    make_pack(source, ids=('X',))
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    output = tmp_path / 'output'
    output.mkdir()
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'checker.py'), str(source)]
    result = subprocess.run(command, cwd=output, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (output / 'flags.csv').read_text().splitlines()[0] == 'station_id,channel,start_utc,end_utc,issue,action,note'
    assert not (source / 'flags.csv').exists()
    assert all(p.read_bytes() == value for p, value in before.items())
    (source / 'stations.csv').write_text('wrong\n')
    previous = (output / 'flags.csv').read_bytes()
    result = subprocess.run(command, cwd=output, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'error' in result.stderr.lower()
    assert (output / 'flags.csv').read_bytes() == previous
