import json
from tests.helpers import make_pack
from ridgeline.io import load_pack, load_report_context, fingerprint
from ridgeline.checks import check_basic
from ridgeline.decisions import decide
from ridgeline.report import render_report


def test_context_is_tied_to_input_and_station_ids(tmp_path):
    make_pack(tmp_path/'pack',ids=('A',));pack=load_pack(tmp_path/'pack')
    assert load_report_context(tmp_path,pack.input_hashes,set(pack.weather)) is None
    path=tmp_path/'report_context.json'
    context=dict(input_fingerprint='stale',station_id='A',first_check='Compare pressure',tasks=['Check board'],runner_up='A',reason='Evidence supports it')
    path.write_text(json.dumps(context))
    assert load_report_context(tmp_path,pack.input_hashes,set(pack.weather)) is None
    context['input_fingerprint']=fingerprint(pack.input_hashes);path.write_text(json.dumps(context))
    assert load_report_context(tmp_path,pack.input_hashes,set(pack.weather))['station_id']=='A'
    context['station_id']='unknown';path.write_text(json.dumps(context))
    assert load_report_context(tmp_path,pack.input_hashes,set(pack.weather)) is None


def test_report_escapes_inputs_and_has_native_details_and_print_css(tmp_path):
    make_pack(tmp_path,ids=('A',));pack=load_pack(tmp_path)
    pack.stations.loc['A','name']='<script>alert(1)</script>'
    result=decide(pack,check_basic(pack))
    html=render_report(result,None)
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert '<details' in html and '<summary' in html and '@media print' in html
    assert '@page' in html and 'A4' in html
    assert 'Visit recommendation pending review' in html
    assert 'https://' not in html and 'http://' not in html
    assert 'flags.csv' in html


def test_report_context_and_all_discovered_stations_render(tmp_path):
    ids=tuple(f'Z{i}' for i in range(18));make_pack(tmp_path,days=.25,ids=ids)
    pack=load_pack(tmp_path);result=decide(pack,check_basic(pack))
    context=dict(station_id='Z0',first_check='Inspect reference pressure',tasks=['0-10 min: inspect','10-60 min: compare'],runner_up='Z1',reason='Persistent pressure offset')
    html=render_report(result,context)
    assert 'Inspect reference pressure' in html and 'Persistent pressure offset' in html
    assert all(f'>{station}<' in html for station in ids)
