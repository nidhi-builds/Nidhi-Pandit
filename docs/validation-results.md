# Validation results

Engineering evaluated on 2026-10-25. The checker is implemented; the final submission still requires the applicant-owned items in SUBMISSION_CHECKLIST.md.

## Release gates

| Gate | Actual result | Status |
|---|---|---|
| G1: contract/reproducibility | Core contract cases pass; three original-pack runs produced identical CSV/JSON/HTML; ZIP input hashes unchanged | Passed |
| G2: fault decisions | 140 locked positive parent cases, 20 per family; 140 equal-duration controls; every family precision/recall 100% | Passed on stated footprint |
| G3: preserve valid observations | Worst family good-data loss 0.04998% (gradual bias); other families 0%; canonical controls have no wrongful exclusions/corrections | Passed (limit 1%) |
| G4: boundaries/evidence | Exact structural fixtures pass; locked flatline/spike/step/rain boundaries exact, conditional at most 30 minutes and gradual at most 24 hours; source/rule evidence and allowed corrections checked | Passed within declared tolerances |
| G5: original pack and delivery | All 39 flags checked against source; 112 fixed-seed unflagged windows visually reviewed; Chrome prints 2 A4 pages; personal submission tasks pending | Engineering checks pass; delivery open |

## Locked benchmark

| Family | Independent positive cases | Matched interval fragments | FP | FN | Precision | Recall | Good-data loss | Max boundary error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| flatline | 20 | 20 | 0 | 0 | 100% | 100% | 0.00000% | 0 min |
| spike | 20 | 20 | 0 | 0 | 100% | 100% | 0.00000% | 0 min |
| additive | 20 | 20 | 0 | 0 | 100% | 100% | 0.00000% | 0 min |
| multiplicative | 20 | 20 | 0 | 0 | 100% | 100% | 0.00000% | 0 min |
| gradual | 20 | 20 | 0 | 0 | 100% | 100% | 0.04998% | 1440 min |
| conditional | 20 | 292 | 0 | 0 | 100% | 100% | 0.00000% | 30 min |
| rain | 20 | 80 | 0 | 0 | 100% | 100% | 0.00000% | 0 min |

There are 140 independent positive parent cases and 472 matched interval fragments. Daylight/rain fragments are correlated within a parent case and are not presented as independent samples. These are measured point estimates on the sampled synthetic scenarios, not a guarantee about all weather, the entire target envelope, or the original pack. Exact footprint and denominators are in EVALUATION.md; per-family machine-readable records are in benchmark-results/.

## Executed tests and independence

- Core: 62 passed with the explicit core-file pytest command recorded in the ledger.
- Development: `python -m pytest tests/test_development.py -q --basetemp=tmp/pytest-development-sealed` ? 7 groups passed, 147.44 seconds; each group contains 20 fault cases and 20 controls.
- First locked run: `python -m pytest tests/test_benchmark.py -q --basetemp=tmp/pytest-final-locked` ? 7 groups passed, 143.54 seconds.
- All 76 collected tests were executed and passed across these three commands on the final detector. The locked run was not used for tuning and has not been called a new holdout on repeat.
- Rule, generator, scorer and manifest hashes were frozen before the first locked run in evaluation-freeze.json. Final result fingerprints match that freeze.
- A previous development spike run failed at 80% recall. It is preserved in development-failure.json. The return check was corrected using a failing trend regression before the final freeze.
- An independent code review found five Important issues; all were reproduced and fixed with regressions. See code-review.md.

## Original-pack findings

- Input: 48,314 rows. Verified duplicate copies: 144. Observed rows after deduplication: 48,170. Missing expected observations: 214 at S08.
- 39 final flag intervals: S02 pressure bias; S03 one 481-sample flatline and four spikes; S05 29 humidity-domain intervals covering 451 readings plus a coordinate mismatch; S06 one supported clock correction; S08 one missing-record interval and one replay/deduplication interval.
- Two review intervals retain the ten S06 edge records outside supporting GPS anchors. No clock extrapolation is applied.
- S02 pressure has independent 48-hour pre/post relative shifts of 6.7 hPa against S03 and 6.6 hPa against S04. Bias is excluded pending calibration rather than automatically subtracting a guessed sensor offset.
- Every output row was reconciled with its source evidence. Full-series review covered all 56 station/channel combinations; 112 six-hour unflagged windows were additionally inspected. Audit summaries are in original-audit-summary.json; full private source plots remain outside git.
- S04 temperature/rain and S07 wind remain explicit investigation limits. No authoritative original-pack labels were supplied, so no overall original-pack accuracy percentage is claimed.
- The S02 technician recommendation is a proposal. The applicant must review its priorities, availability of a calibrated portable reference and the runner-up reasoning.

## Operational and browser checks

- Three original-pack in-process CLI runs took [3.655, 3.335, 3.404] seconds; peak process working set was 137.9 MB. These are local diagnostics, not performance guarantees; timings exclude interpreter startup.
- CSV, review, evidence and rendered HTML hashes were identical across those runs. All input bytes still match the supplied ZIP.
- Chrome: native Tab/Enter opens evidence disclosure; 390-pixel mobile viewport has no body overflow; actual print-to-PDF output is two A4 pages. Screenshots and print artifacts were inspected and kept private; browser-verification.json records the checks.
- Source inspection found no assignment station IDs or incident dates embedded in checker rules. Renaming stations and changing file discovery order preserve equivalent decisions. Network-denied and different-working-directory tests pass.

## Remaining submission work

README name/email are filled and the project is published at https://github.com/nidhi-builds/Nidhi-Pandit. DECISIONS.md is intentionally retained locally and excluded from published history, as requested. The video link, personally written decisions, independent no-AI hand calculation, genuine full AI-chat exports, visit confirmation and submission form remain with the applicant.
