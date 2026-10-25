import json
from pathlib import Path
import pytest
from tests.benchmark_cases import FAMILIES, scenario
from tests.metrics import candidate_rows, evaluate, good_data_loss
from ridgeline.io import load_pack
from ridgeline.checks import check_basic
from ridgeline.relationships import check_relationships


@pytest.mark.parametrize('family',FAMILIES)
def test_development_gate(tmp_path,family):
    totals={'tp':0,'fp':0,'fn':0}; boundaries=[]
    lost=good=0
    for number in range(20):
        seed=(11,23,37)[number%3]+number*1009
        truth,frames,cadence=scenario(tmp_path/str(number),seed,family)
        pack=load_pack(tmp_path/str(number)); basic=check_basic(pack)
        predictions=candidate_rows(basic+check_relationships(pack,basic))
        result=evaluate(predictions,truth,cadence)
        for key in totals: totals[key]+=result[key]
        boundaries+=result['boundary_minutes']
        a,b=good_data_loss(predictions,truth,frames);lost+=a;good+=b
        limit=cadence if family in ('flatline','spike') else 1440 if family=='gradual' else 360
        assert not result['boundary_minutes'] or sum(v<=limit for v in result['boundary_minutes'])/len(result['boundary_minutes'])>=.9
        _,control_frames,_=scenario(tmp_path/f'control-{number}',seed,family,control=True)
        control_pack=load_pack(tmp_path/f'control-{number}');control_basic=check_basic(control_pack)
        control_predictions=candidate_rows(control_basic+check_relationships(control_pack,control_basic))
        a,b=good_data_loss(control_predictions,[],control_frames);lost+=a;good+=b
        assert not control_predictions,control_predictions
    precision=totals['tp']/(totals['tp']+totals['fp']) if totals['tp']+totals['fp'] else 0
    recall=totals['tp']/(totals['tp']+totals['fn'])
    record=dict(totals,precision=precision,recall=recall,independent_cases=20,control_cases=20,boundary_minutes=boundaries,good_cells=good,lost_good_cells=lost,good_data_loss=lost/good)
    output=Path('private/development-results');output.mkdir(parents=True,exist_ok=True)
    (output/f'{family}.json').write_text(json.dumps(record,indent=2))
    assert precision>=.95 and recall>=.90,record
    assert lost/good<=.01,record
