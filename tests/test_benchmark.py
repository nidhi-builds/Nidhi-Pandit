"""Locked final benchmark. Re-run unchanged for regression; never tune on these labels."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import pytest
from checker import investigate
from tests.benchmark_cases import FAMILIES,scenario
from tests.metrics import evaluate,good_data_loss


@pytest.mark.parametrize('family',FAMILIES)
def test_locked_benchmark(tmp_path,family):
    manifest=json.loads(Path('tests/manifests.json').read_text())
    totals={'tp':0,'fp':0,'fn':0};lost=good=0;boundaries=[];parents=0
    for seed in manifest['final_seeds']:
        truth,frames,cadence=scenario(tmp_path/str(seed),seed,family)
        result=investigate(tmp_path/str(seed))
        predicted=[dict(station_id=f.station_id,channel=f.channel,issue=f.issue,action=f.action,start=f.start_utc,end=f.end_utc) for f in result.flags if f.action!='keep']
        assert not any(f.action=='keep' for f in result.flags),'Injected faults must not receive keep'
        score=evaluate(predicted,truth,cadence);parents+=1
        for key in totals:totals[key]+=score[key]
        boundaries+=score['boundary_minutes']
        a,b=good_data_loss(predicted,truth,frames);lost+=a;good+=b
        tolerance=cadence if family in ('flatline','spike') else 1440 if family=='gradual' else 360
        assert not score['boundary_minutes'] or sum(v<=tolerance for v in score['boundary_minutes'])/len(score['boundary_minutes'])>=.9
        _,controls,_=scenario(tmp_path/f'control-{seed}',seed,family,control=True)
        clean=investigate(tmp_path/f'control-{seed}')
        clean_predictions=[dict(station_id=f.station_id,channel=f.channel,issue=f.issue,action=f.action,start=f.start_utc,end=f.end_utc) for f in clean.flags if f.action!='keep']
        a,b=good_data_loss(clean_predictions,[],controls);lost+=a;good+=b
        assert not clean_predictions,clean_predictions
    precision=totals['tp']/(totals['tp']+totals['fp']) if totals['tp']+totals['fp'] else 0
    recall=totals['tp']/(totals['tp']+totals['fn'])
    record=dict(totals,precision=precision,recall=recall,independent_cases=parents,control_cases=parents,
                max_boundary_minutes=max(boundaries,default=None),good_cells=good,lost_good_cells=lost,good_data_loss=lost/good,
                rule_fingerprint=result.evidence['rule_fingerprint'],manifest_sha256=hashlib.sha256(Path('tests/manifests.json').read_bytes()).hexdigest())
    output=Path('docs/benchmark-results');output.mkdir(exist_ok=True)
    (output/f'{family}.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    assert precision>=.95 and recall>=.90,record
    assert lost/good<=.01,record
