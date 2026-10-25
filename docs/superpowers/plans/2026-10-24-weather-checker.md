# Weather Checker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for implementation in this session, or superpowers:subagent-driven-development if the user selects delegated execution. Execute tasks in order; each stage must pass its gate before the next dependent stage.

**Goal:** Deliver an offline, explainable weather-data checker, defensible flags and an actionable printable coordinator report.

**Architecture:** Preserve raw inputs and provenance, establish time integrity, detect candidates, corroborate relationships, then apply explicit decision rules. Generate deterministic CSV/JSON evidence and a static HTML report. Human investigation informs the evaluation ledger and technician recommendation, not hidden station-specific detection rules.

**Tech Stack:** Python 3.11+, pandas, NumPy, Matplotlib, standard library, pytest; plain HTML/CSS and native `<details>` elements. Pin tested dependency versions. No runtime AI, server or JavaScript framework.

**Spec:** [Design](../specs/2026-10-24-weather-checker-design.md). **Gates:** [Evaluation contract](../../EVALUATION.md).

**Status:** Engineering execution completed and evaluated on 2026-10-25; applicant-owned submission tasks remain pending. Exact per-stage evidence and refinements are in docs/execution-ledger.md, and actual scores are in docs/validation-results.md. The original estimate was 10-14 focused hours plus applicant writing/recording; do not treat it as measured elapsed effort.

## Global constraints

- CLI: `python checker.py <pack-folder>`; outputs in current working directory.
- `flags.csv` schema: `station_id,channel,start_utc,end_utc,issue,action,note`.
- No runtime AI, external APIs, downloads, paid services or input mutation.
- Nine fault names and one non-fault keep name, exactly as specified in the design.
- Use metadata cadence and dynamic station discovery. No hardcoded station IDs, dates or supplied incident locations.
- Original pack and full raw copies must never be tracked by git. Only synthetic fixtures are public.
- Required report print length <=2 A4 pages; one page preferred.
- Preserve complete real AI logs. Applicant writes DECISIONS.md and completes the no-AI calculation personally.
- An unmet gate is not permission to reduce thresholds, remove tests or claim completion.

## Review focus

1. Clock reset creates duplicate labels: retain row identity and diagnose time before destructive deduplication (Stages 1-2).
2. Genuine saturation, dry weather and local rain: prevent naive flatline/cross-station exclusions (Stages 3-4).
3. Corrupted or absent references: disclose insufficient evidence instead of fabricating certainty (Stage 4).
4. Mixed good/bad intervals and overlapping flags: correct availability totals and no blanket station rejection (Stages 5-6).
5. Short/shifted/cadence-varied packs and invalid schema: gracefully restrict supported inference; fail malformed required input clearly (Stages 1, 4, 7).

## File responsibilities

```text
checker.py                     CLI entry point; orchestration and exit codes
ridgeline/types.py             Pack, Candidate, Flag, RunResult dataclasses
ridgeline/io.py                Load/validate input; provenance; atomic output
ridgeline/config.py            Versioned thresholds and fixed seed settings
ridgeline/gps.py               NMEA validation; time/position evidence
ridgeline/checks.py            Missing/duplicate/domain/flatline/spike candidates
ridgeline/relationships.py     Reference selection; residuals; bias/rain/solar evidence
ridgeline/reference.py         Shared clean hourly data and basic-reference eligibility
ridgeline/decisions.py         Actions, consolidation and evidence templates
ridgeline/report.py            Summary counts, embedded plots and HTML renderer
tests/test_io.py               Input contract and provenance
tests/test_gps.py              GPS and clock/coordinate fixtures
tests/test_checks.py           Basic fault and normal-channel fixtures
tests/test_relationships.py    Relational faults and reference failure controls
tests/test_decisions.py        Action/conflict/deduplication/interval semantics
tests/test_report.py           Counts, escaped HTML and print-facing content
tests/test_end_to_end.py       CLI, offline run, preservation and determinism
tests/benchmark_cases.py       Independent synthetic scenarios and fault injection
tests/test_benchmark.py        Matching, metrics and locked benchmark execution
tests/fixtures/                Synthetic inputs and independent calculation fixtures
report_context.json           Applicant-reviewed visit recommendation; no invented content
requirements.txt              Pinned runtime dependencies
requirements-dev.txt          Runtime requirements plus pinned pytest
README.md                     Assignment entry point; run command and limitations
DECISIONS.md                   Applicant's five responses
ai_logs/                      Genuine exported conversations
docs/EVALUATION.md             Single source of truth for all release metrics
docs/validation-results.md     Actual measured results, counts and failures
```

Keep modules small and ordinary functions. No plugin framework or dependency injection system. Configuration is code/constants with a version, not a user-facing settings UI.

## Shared interfaces

Define these once in Stage 1; later stages consume them rather than inventing parallel models:

- `Pack`: `stations: DataFrame`, `weather: dict[str, DataFrame]`, `gps_lines: dict[str, list[str]]`, `maintenance_text: str`, `input_hashes: dict[str, str]`, `diagnostics: list[dict]`. Weather frames include source path/row number/raw time, parsed logger time and nullable analysis time.
- `Candidate`: `station_id: str`, `channel: str`, `issue: str`, `subtype: str`, `start: datetime | None`, `end: datetime | None`, `row_refs: tuple[str, ...]`, `evidence: dict`. No provisional final action field.
- `Flag`: exactly the seven CSV fields as strings. Source evidence remains in the sidecar.
- `RunResult`: `flags: list[Flag]`, `reviews: list[dict]`, `evidence: dict`, `summary: dict`.
- `load_pack(folder: Path) -> Pack`.
- `audit_gps(pack: Pack) -> list[Candidate]`; writes only explicitly supported in-memory analysis-time fields through `apply_supported_time_map(pack, candidates) -> Pack` with copied weather frames.
- `check_basic(pack: Pack) -> list[Candidate]`.
- `check_relationships(pack: Pack, basic: list[Candidate]) -> list[Candidate]`.
- `decide(pack: Pack, candidates: list[Candidate]) -> RunResult`.
- `render_report(result: RunResult, context: dict | None) -> str`.
- `load_report_context(output_dir: Path, input_hashes: dict[str, str], station_ids: set[str]) -> dict | None` in `io.py`; validate optional current-directory context against the canonical input fingerprint and report stale/invalid context as a diagnostic.
- `write_outputs(result: RunResult, html: str, output_dir: Path) -> None`.

Internally distinguish raw row identity from timestamp. No interval-only mapping may erase that distinction.

## Stage 0 - Documentation, privacy and evaluation setup

**Files:** starter README/DECISIONS/AI-log guide, design, evaluation contract, `.gitignore` at execution start.

- [ ] Review the design and gates with the applicant; record any changes explicitly.
- [ ] Initialize git at implementation start and add ignore rules for the ZIP/PDF source brief, private extracted pack, `tmp/`, environments, caches and local review ledgers. Do not blanket-ignore the final required `flags.csv` or report.
- [ ] Commit only the reviewed documentation and ignore rules; inspect staged paths first.
- [ ] Establish development/final-test manifests, canonical control cases, expected truth format and synthetic-only public fixture policy.
- [ ] Record unknown personal details as placeholders; establish the actual deadline from the invitation rather than guessing.

**Gate:** Every assignment deliverable has an owner/path; required input files are untracked; metric definitions and fault vocabulary are fixed. No claim of checker readiness.

## Stage 1 - Reliable ingestion and minimal end-to-end command

**Create:** `checker.py`, `ridgeline/types.py`, `ridgeline/io.py`, `ridgeline/config.py`, requirements, `tests/test_io.py`, first end-to-end fixture.

**Interfaces:** implement `load_pack` and the shared types; start a command that writes a header-only flags file for a clean synthetic input. Later stages supply actual decisions.

- [ ] Write tests for alternate station names, metadata cadence, paths with spaces, missing optional GPS/notes, bad required schema, missing weather files and numeric parse failures.
- [ ] Assert required-schema failure exits nonzero and writes no new output; successful runs preserve raw row numbers and source hashes.
- [ ] Run `python -m pytest tests/test_io.py -q` and observe meaningful failures before implementation.
- [ ] Implement validated loading, provenance and deterministic serialization with UTF-8/newline rules. Write output through temporary files only after validation.
- [ ] Run I/O tests and a subprocess invocation from another working directory; verify unchanged input hashes and exact seven-column header.
- [ ] Commit this independently runnable ingestion slice.

**Gate:** G1 contract cases for ingestion all pass; no input loss, silent timestamp rewriting or unexpected directory writes.

## Stage 2 - GPS, clocks, missing data and duplicates

**Create:** `ridgeline/gps.py`, structural portion of `checks.py`, `tests/test_gps.py`, structural tests in `test_checks.py`.

**Interfaces:** implement `audit_gps`, `apply_supported_time_map`, structural portion of `check_basic`.

- [ ] Write synthetic RMC/GGA fixtures with independently computed checksums, southern/western coordinates, midnight rollover, invalid status, bad checksum and missing dates.
- [ ] Write known-answer fixed-offset, reset, drift, duplicate/conflict and cadence-aware gap tests. A reset-induced collision must not delete distinct observations.
- [ ] Run `python -m pytest tests/test_gps.py tests/test_checks.py -q`; verify the new tests fail for the absent behaviours.
- [ ] Implement GPS evidence filtering and constant-offset correction eligibility; detect drift/jumps without promising automatic interpolation.
- [ ] Implement structural candidates; compute gaps on supported analysis time, retain original labels/provenance, and exclude unknown installation edges from invented gaps.
- [ ] Rerun tests; verify all known structural events and allowed corrections exactly, including direction of the clock offset.
- [ ] Commit.

**Gate:** G2 structural fixtures at 100% precision/recall; G4 structural boundaries within one interval; all correction fixtures pass. Invalid GPS produces no unsupported correction.

## Stage 3 - Original-pack evidence inventory and basic sensors

**Create:** remaining `checks.py`, basic tests, private `original_pack_review.csv` and private investigation plots.

**Interfaces:** complete `check_basic`; preserve separate candidates/evidence rather than writing final action prose inside detectors.

- [ ] Inspect all station/channel series and GPS time comparisons; record the initial independent evidence ledger before writing relationship detectors. Preserve uncertainty and alternative explanations.
- [ ] Write domain, spike and flatline tests, including 100% RH episodes, calm wind, dry rain, dark irradiance, zero-MAD series and wind-direction wrap.
- [ ] Run `python -m pytest tests/test_checks.py -q` and verify new assertions fail before implementing those checks.
- [ ] Implement candidate logic using design thresholds and documented per-channel floors; never infer sensor failure from constant zero rainfall or night irradiance.
- [ ] Rerun the basic controls and fault fixtures. Capture source snippets for candidate events but do not label every suspicious case confirmed.
- [ ] Commit code/tests and sanitized investigation summary; never stage private raw data or full local ledger snippets.

**Gate:** All hard-domain fixtures pass; all applicable canonical normal-weather controls pass. Every original station/channel has been inspected; uncertain events are explicitly labelled uncertain. Candidate counts are not advertised as fault accuracy.

## Stage 4 - Normal relationships and cross-channel corroboration

**Create:** `ridgeline/relationships.py`, `tests/test_relationships.py`, development scenario generator in `tests/benchmark_cases.py`.

**Interfaces:** `check_relationships(pack, basic)` produces evidence-rich candidates; no runtime maintenance-language interpretation.

- [ ] Write paired cases: elevation differences versus pressure offset; real front versus spike; genuine humid weather versus flatline; true local rain versus supported underresponse; changing sunshine versus injected temperature radiation bias.
- [ ] Add additive, wind-scale and gradual-drift cases with qualified references, plus corrupted-reference, short-pack, no-overlap and simultaneous-reference-failure cases.
- [ ] Run `python -m pytest tests/test_relationships.py -q`; observe failures for the new capabilities.
- [ ] Implement capped reference selection, robust residual comparisons, day/night matching and one controlled refit after exclusions. Keep high-frequency native data for event localization.
- [ ] Implement solar context from the cited NOAA method; compare independent fixtures at other sites/dates, never generate the applicant's by-hand response.
- [ ] Implement bias subtypes and rain evidence; cases lacking required context become review candidates. Freeze numeric floors and eligibility rules in `config.py` with justifications.
- [ ] Run development benchmark and canonical controls; inspect failure explanations rather than raising thresholds to hide them.
- [ ] Commit the reference logic, tests and frozen detector configuration.

**Gate:** Development G2 precision >=95% / recall >=90% per supported sensor subtype; G3 <=1% good-data loss and all canonical controls pass; evidence completeness 100%. This is a development gate, not a final held-out score.

## Stage 5 - Final flags, audit evidence and unresolved cases

**Create:** `ridgeline/decisions.py`, `tests/test_decisions.py`; complete output serialization.

**Interfaces:** implement `decide` and `write_outputs`; deterministic note templates interpolate measurements and explicit limitations.

- [ ] Write tests for exact schema/vocabulary, identical-duplicate correction versus conflicting values, narrow channel exclusions, clock superseding solar symptoms, flatline superseding bias, and adjacent versus separated intervals.
- [ ] Test that uncertain candidates appear only in `review.csv`, every correction names an allowed procedure, and `keep` cannot override a confirmed fault. Assert metadata mismatch uses metadata/exclude without removing weather and reset intervals carry ordered labels plus source row ranges in notes.
- [ ] Run `python -m pytest tests/test_decisions.py -q`; confirm new assertions fail before implementing.
- [ ] Implement precedence/consolidation and stable evidence linkage. Keep physical thresholds, eligibility and interpretation out of the HTML renderer.
- [ ] Recompute evidence quantities independently in tests and validate every sidecar link and interval basis.
- [ ] Run the CLI three times on the same input and compare `flags.csv` bytes and deterministic JSON evidence; compare input hashes before/after.
- [ ] Commit.

**Gate:** G1 and G4 contract/evidence requirements all pass; all correction fixtures pass; no redundant derivative flags or undocumented actions.

## Stage 6 - Coordinator frontend and technician recommendation

**Create:** `ridgeline/report.py`, `tests/test_report.py`, applicant-reviewed `report_context.json`.

**Interfaces:** implement `render_report`; consume `RunResult` without rerunning scientific decisions.

- [ ] Write count tests with overlapping exclusions, missing intervals, correctable duplicates, keep flags and metadata-only discrepancies; verify disjoint denominators.
- [ ] Write HTML checks for escaped station names/notes, no external assets, visible uncertainty and pending visit recommendation when context is absent, malformed or belongs to another input fingerprint. Test dynamic station counts and condensed printing for larger packs.
- [ ] Run `python -m pytest tests/test_report.py -q`; observe failures before implementation.
- [ ] Implement fingerprint-validated context discovery from the working directory. Build one static report: usability summary, station/channel matrix, consequential intervals, limited evidence plots and a one-hour visit recommendation with runner-up.
- [ ] Add native expandable screen-only evidence panels and print styling; no app routing, upload flow or custom interactive chart system.
- [ ] Use actual investigated evidence to propose the visit; the applicant reviews what to check first, tasks and runner-up reasoning. Do not synthesize a decision from an unexplained composite score.
- [ ] Open in a real browser; inspect keyboard operation and A4 print preview. Check grayscale legibility, clipping and <=2 pages. Save local visual verification evidence.
- [ ] Commit.

**Gate:** All report count/escaping tests pass; the two coordinator questions are answered; report prints in <=2 A4 pages and contains no invented confirmed findings.

## Stage 7 - Locked evaluation, original-pack audit and submission

**Create:** `tests/test_benchmark.py`, complete `test_end_to_end.py`, `docs/validation-results.md`; finalize assignment files.

**Interfaces:** `evaluate(predictions, truth, cadence_minutes) -> dict` in benchmark test utilities, implementing the evaluation contract independently of detector functions.

- [ ] Test the scorer itself with perfect predictions, duplicate predictions, wrong actions, missed faults and interval overreach. Exact known fractions must match. Use direct assertions for overlapping-fault stress cases and observation-level truth intervals for conditional bias/rain, retaining parent-episode IDs to avoid inflated sample counts.
- [ ] Freeze detector config/input/test manifests; run `python -m pytest -q` including the locked benchmark. Save per-subtype TP/FP/FN, parent-episode/fragment counts, boundary errors, good-data loss and coverage.
- [ ] If final-test inspection drives code changes, retain the failure, move those cases to regression and create a fresh final manifest. Do not relabel a tuned-on test as held out.
- [ ] Run `python checker.py <private-original-pack-folder>` from the submission directory; audit every resulting flag, correction and keep against the independent ledger and source evidence.
- [ ] Sample unflagged intervals as specified in EVALUATION.md; investigate misses and maintain uncertainty. Report reviewed-subset results separately from synthetic scores.
- [ ] Run offline/from a different directory; verify deterministic outputs, unchanged inputs, and no network use.
- [ ] Fill `docs/validation-results.md` with actual results and remaining limitations. Finalize README with applicant name/email/video link and tested run command.
- [ ] Applicant writes DECISIONS.md in their own words, including genuine AI mistakes and the independent no-AI calculation. Do not invent anecdotes or AI-chat exports.
- [ ] Export full real AI chats; applicant records the three-minute evidence demonstration. Inspect staged files for accidental pack disclosure and incremental commit history.
- [ ] Review final repository naming and submission checklist. Publication/form submission occur only within the user's authorized scope and the assignment's timing constraints.

**Gate:** G1-G5 all pass and actual results are recorded. No placeholder identity, video, decisions, visit recommendation or false performance claim in the final submission. Uncertain original-pack cases are disclosed, not silently scored as correct.

## Completion rule

Finish only when the tested command and required artifacts exist, the stated gates have measured results, and the applicant-owned deliverables are genuinely complete. A failing detector is a documented failure, not a reason to add runtime AI. Any later AI proposal requires a controlled comparison showing better decisions without worse corrections, false exclusions or traceability.
