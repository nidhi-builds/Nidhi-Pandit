# Execution ledger - docs/superpowers/plans/2026-10-24-weather-checker.md

User approved execution on 2026-10-25, using Ponytail and Superpowers, with successive stage gates.

## Rulings

- Ruling: execute inline in the requested workspace on a new implementation branch; this is a new repository with no existing code or shared branch to protect. A second checkout adds no isolation benefit here. No merge or publication is authorized by this action.
- Ruling: use this tracked ledger and native PowerShell commands instead of the skills' Bash bookkeeping scripts; preserve the same gate, test and commit evidence without introducing shell dependencies.
- Pre-flight: Stage 1 Pack/provenance feeds GPS/basic checks (2-3), relationship evidence (4), decisions (5), report (6), evaluation (7). Shared interfaces agree; source row identity must survive every stage.
- Pre-flight: independent frontend work may proceed after a scientific gate fails only if clearly labelled unevaluated; final release cannot pass with failed scientific gates. No target reductions are authorized.
- Personal name/email, invitation deadline, applicant-authored decisions, actual AI exports and recording cannot be invented; these remain submission prerequisites, not blockers to local engineering.

## Stage status

| Stage | Status | Evidence |
|---|---|---|
| 0 | Passed | fbf0546: plan committed; ZIP/PDF excluded from tracking |
| 1 | Passed | RED: missing ridgeline module; GREEN: 7 I/O tests, 2026-10-25 |
| 2 | Passed | 13 combined tests pass; GPS/parser, offset/drift, gaps, duplicates, provenance |
| 3 | Passed | 15 tests; 56 station/channel plots reviewed; independent evidence ledger frozen |
| 4 | Passed | 140 fault cases + 140 matched controls; per-family precision/recall 100%; good-data loss 0 |
| 5 | Pending | |
| 6 | Pending | |
| 7 | Pending | |

- Stage 1 environment ruling: pytest temp-directory ACLs require an escalated local test run; `python -m pytest tests/test_io.py -q` passed 7/7. Test artifacts remain under ignored tmp/. Dependencies were already installed; no download needed.

- Stage 2 RED: absent GPS/basic modules. A structural regression exposed an invented gap between appended retransmissions; fixed by checking whether expected observations already exist. GREEN: 13/13 combined tests. Final benchmark remains pending.

- Stage 3: original-pack ledger frozen before relational code, with direct/uncertain labels separated. RED sensor assertions failed; GREEN 15/15 combined tests. Full data and plots remain private.

- Stage 4 RED: relational module missing; GREEN: 10 relational controls, 140 independent development faults and 140 equal-duration controls. Every family met its target and boundary gate; details in docs/development-results.json. Final seeds remain untested.
- Stage 4 investigation reopened Stage 2: GPS reception jitter versus minute labels caused a false gap, and NaT clock-edge rows could be mistaken for confirmed duplicates. Each received a failing regression, root-cause fix and passing clock/basic suite (10/10). Edges outside GPS coverage remain unverified, not extrapolated.
- Tooling incident: two pytest runs shared a basetemp. The complete development run ultimately passed; subsequent concurrent runs use separate workspace-local basetemps. No original inputs changed.
