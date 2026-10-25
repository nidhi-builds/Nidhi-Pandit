# Checker evaluation contract

Status: frozen engineering gates, evaluated on 2026-10-25. Actual results and remaining applicant-owned submission items are in [validation-results.md](validation-results.md). Targets below remain acceptance criteria, not universal accuracy guarantees.

## Five release gates

| Gate | Exact requirement |
|---|---|
| G1: correctness and reproducibility | 100% contract and safety fixtures pass; three identical runs in the pinned environment produce identical flags and semantic evidence; input hashes unchanged |
| G2: fault decisions | Structural fixtures: 100% precision/recall. Relational/sensor benchmark: event precision >=95% and recall >=90% for EACH supported subtype with at least 20 independently generated positive events |
| G3: preserve valid weather | False exclusion/correction rate <=1% of known-good observed channel cells over held-out controls; zero wrongful exclusions/corrections in each named canonical normal-weather fixture |
| G4: locate and justify | At least 90% of matched structural/basic events have both boundaries within one logging interval; relational events within six hours (drift within one day); 100% final flags have complete reproducible evidence and permitted action |
| G5: original-pack and delivery audit | 100% final original-pack flags manually reviewed; zero known contradictions or unsupported corrections; all known confirmed detectable events accounted for; every unresolved case disclosed; original command works offline from a different working directory and report prints in <=2 A4 pages |

G2's high percentages are engineering acceptance targets, not statistical certainty about deployment. Report numerator, denominator, independent parent-episode count and interval-fragment count for precision/recall. Do not attach an independence-based confidence interval to correlated fragments. Small sample sizes must remain visible. No average may conceal a failing subtype. If a subtype emits no predictions, precision is N/A, not 100%; recall fails when known events are missed.

## Metric definitions

- **Event match:** same station, channel, issue and correct action; overlap on the canonical expected cadence grid with intersection/union >=0.5. For isolated nonoverlapping benchmark events, sort eligible pairs by descending overlap score, break ties by stable truth/prediction row order, and greedily accept only unused pairs. One giant interval cannot match many faults. Score overlapping-fault stress cases with direct expected-outcome assertions rather than this simplified matcher. `all` expands to the affected channel set for scoring without multiplying one structural event into seven independent successes.
- **Precision:** matched predicted events / all predicted fault events. A wrong action is an unmatched prediction and leaves its true event missed. Unsupported extra flags are false positives in fully labelled synthetic cases.
- **Recall:** matched predicted events / all known in-scope fault events. Review/abstention on a known supported fault counts as a miss; it is not removed from the denominator.
- **Good-data loss:** union of known-good observed channel cells marked exclude or subject to a wrong correction / all known-good observed channel cells. Extra duplicate copies are not good cells. A correct clock mapping or correct deduplication is not loss. Count overlapping flags once.
- **Boundary error:** absolute difference between predicted and true first/last affected grid points. Report both endpoints. Use original raw label plus provenance to map corrected-clock cases to unique truth records.
- **Correction correctness:** verified duplicates leave exactly one intended observation; GPS constant-offset correction has <=60 seconds absolute timestamp error, preserves order within a segment, and creates no unexplained collisions. Every correction case must pass; no averaging away a wrong correction.
- **Evidence completeness:** required rule/config version, source identifiers, action, quantities, applicable thresholds, time basis and limits are present; independent recomputation agrees within stated numerical precision. Narrative polish is not evidence.
- **Coverage diagnostics:** publish eligible/evaluated/unevaluated cell counts, review-event count and disabled-check reasons by station/channel. These are transparency measures, not substitute accuracy scores.
- **Keep decisions:** separate from fault precision/recall. Every predicted keep in fully labelled fixtures must concern a real event, not an injected fault. A confidently wrong keep fails the release gate. No minimum keep count encourages unnecessary flags.

## Known-answer test design

Use synthetic multi-station weather with shared regional variation plus station offsets, local variation, day/night effects and independent noise. Construct the generator separately from detector logic; it must not import detector thresholds or functions. Cover at least three independent underlying weather scenarios. Vary station IDs, station count, dates, cadence, elevation and fault placement. Tests must not encode S01-S08 or March/April 2025 as privileged cases.

Provide separate development and locked final-test seed manifests. Freeze detector configuration and test-case hashes before running the final manifest. If final-test failures are used for tuning, retire that manifest to regression and generate a new held-out manifest; keep the failed result in the audit. Merely rerunning the same final test is not a fresh holdout.

For each sensor/relational subtype, use at least 20 positive events spread across >=3 independent base scenarios, plus controls of equal total duration. Include overlapping faults in a separate stress suite; do not quietly count every correlated sample as an independent event. Structural exact cases use exhaustive small fixtures rather than arbitrary accuracy percentages.

### Target detection envelope

| Family/subtype | Known positive benchmark cases |
|---|---|
| missing_data | Interior gaps of 1-144 expected records; missing/unparseable channel cells; cadence from metadata |
| duplicate_data | Exact extra copies and conflicts at the same timestamp; replay tests include repeated timestamps/provenance, not merely similar weather |
| clock_error | Supported fixed offsets from 2 minutes to 12 hours; resets into stable offset segments; observable drift >=2 minutes/day over >=3 days; valid GPS support and unique row mapping where correction is expected |
| location_mismatch | Horizontal offsets >=2 km, stable valid GPS for >=24 hours; invalid-fix controls |
| out_of_range | Definite violations of documented RH/rain/wind/direction domains, including boundary values and NaN classification |
| flatline | >=24-hour lost response with changing underlying weather and valid independent evidence; exclude naturally constant channels from positives |
| spike | 1-2-record temperature/pressure/humidity excursions >=8 local robust scales, with return and two trustworthy references |
| sensor_bias: additive | Temperature >=3 C; pressure >=5 hPa; humidity >=15 points; lasting >=48 hours, with >=7 clean baseline days and suitable references |
| sensor_bias: multiplicative | Wind gain >=1.6 or <=0.625 for >=48 hours, adequate non-calm variation and references |
| sensor_bias: gradual | Temperature drift >=3 C or pressure >=5 hPa over >=7 days, adequate clean preceding baseline and suitable references |
| sensor_bias: conditional | >=3 C added temperature excess in high-light/low-wind periods on >=3 days, adequate matched pre-change/control samples |
| rainfall_underresponse | >=3 supported nonfreezing regional episodes; total loss or >=90% reduction, with independently established prior/recovered response; no invented exact onset between events |

Record exact injected intervals and correction truth before running the checker. Events outside this envelope are exploratory results, not promised recall. If inputs satisfy the predeclared envelope but the implementation refuses their references, that remains a miss. Eligibility must come from generator truth or independent labels, not post-hoc detector selection.

The locked benchmark samples this envelope; it does not exhaustively validate every boundary or combination. Its actual footprint is: 72-hour temperature/pressure/humidity flatlines; one/two-record temperature/pressure/humidity spikes; additive changes of 4 C/6 hPa/18 humidity points; wind gains of 0.5 or 1.8; temperature/pressure ramps of 5 units over roughly 14-16 days; 4 C conditional temperature excess; and four complete rain-response losses per parent episode. It varies calendar years/months, station IDs/counts, cadence and base weather. There are 20 independent parent cases per family, not 20 per channel or every parameter value. No numeric accuracy claim is made for untested wind flatlines, smaller amplitudes, short baselines, arbitrary compound failures or the entire target envelope.

Truth intervals represent affected observations, not the duration of the underlying hardware condition. A sunlight-dependent injected bias has separate affected daytime intervals and healthy nights. Rain underresponse truth covers supported wet-episode intervals, not all dry days during a week-long simulated blockage. Store the hardware-condition interval separately for explanation; apply IoU and boundary scoring to observation intervals. Generate at least 20 independent fault episodes per subtype; day/episode fragments from one hardware condition do not satisfy the 20-independent-event requirement by themselves. Show both parent-episode counts and interval counts.

### Exact assignment of metric gates and actions

- G2 exact structural/metadata fixture gate (100%): missing_data/exclude; exact duplicate_data/correct; conflicting duplicate_data/exclude on conflicting channels; out_of_range/exclude; valid fixed clock_error/correct; supported reset segments/correct; supported GPS clock drift/exclude; confirmed location_mismatch/metadata/exclude. Test insufficient-evidence variants as review, with no invented flag.
- G2 statistical gate (>=95% precision, >=90% recall per subtype): flatline/exclude, spike/exclude, sensor_bias/exclude for each of its four subtypes, rainfall_underresponse/exclude. At least 20 independent known-positive parent episodes per subtype.
- G4 clock, metadata and basic event boundaries use the one-cadence tolerance over the independently established supported evidence span; bias/rain boundaries use six hours, gradual sensor drift one day. Metadata span is the qualified GPS span, not an unobserved period before it.
- Wrong action fails matching. Ambiguous synthetic cases have review as the expected outcome and are evaluated by direct assertions; known eligible cases cannot be converted to ambiguous after seeing a miss.

### Canonical normal-weather controls (all must pass)

1. Elevation-related temperature and pressure differences without sensor faults.
2. Regional front and regional hot/cold event shared by suitable stations.
3. Genuine saturated humidity, dry weather, calm wind and night-time zero irradiance.
4. Local rain at one station, snow/freezing ambiguity and legitimate spatial differences.
5. Cloud/shading effects and an imperfect relationship between GHI and temperature.
6. Wind direction wrapping through 359/0 degrees and 360 as a valid equivalent.
7. One corrupted reference, insufficient overlap, absent GPS and invalid GPS checksums.
8. Short packs and changed logging intervals: dependent checks disclose insufficient evidence.

Canonical controls assert zero wrongful exclusion/correction and zero false keep of any attached fault. They do not require every normal interval to emit a keep flag.

## Original-pack investigation

The supplied pack has no authoritative labels and has already been inspected. It is a development/investigation dataset, not an untouched final test.

Before implementing relational detectors, build a local `original_pack_review.csv` with columns `station_id,channel,start_utc,end_utc,candidate_issue,label,evidence,uncertainty`. Labels: `confirmed_fault`, `supported_weather`, `uncertain`. Use full-series plots, GPS comparisons and maintenance context; record contradictory evidence. Do not copy labels from checker output. Review all channels across all eight stations, including apparently normal periods.

Freeze the first evidence ledger before tuning those detectors. Later corrections to labels need an explicit reason independent of the desired score. Development assistance by AI does not turn the ledger into authoritative ground truth; the applicant reviews its interpretations.

After running the checker:
- Review every final flag, correction and keep; connect it to source evidence.
- Reconcile every confirmed in-scope event with a flag or a documented missed detection. A known in-scope miss blocks G5 until fixed or an explicit scope change is approved.
- Inspect unflagged observations using fixed-seed windows across all stations/channels; include every maintenance neighbourhood and at least two six-hour windows per station/channel outside flagged intervals where available. Report when coverage is too short.
- Publish supported precision/recall only on the reviewed labelled subset, with its size and uncertain cases separate. Do not quote an overall original-pack accuracy percentage.
- Run controlled injections into independently reviewed usable segments as supplemental realism tests; keep the unmodified pack and labels separate. These injections are not proof that every unmodified value is correct.

## Regression and operational checks

- Renaming station IDs and reordering directory entries leaves decisions equivalent after inverse mapping; numeric translations of longitude/latitude are not arbitrary invariances.
- Weather row order is provenance and may matter for resets/replays. Do not assert row-shuffle invariance for such cases.
- Running from another working directory writes outputs there, not inside the input pack.
- Missing optional context disables dependent checks visibly; malformed required schema produces a useful nonzero failure with no partial new report.
- HTML escapes hostile input text and uses local assets only; no web requests occur during runtime.
- Three repeated runs produce byte-identical flags; timestamps/durations, if logged for performance, remain outside deterministic evidence.
- Record wall time and peak memory on the eight-station pack as diagnostics. No unsupported 500-station scalability promise; discuss that extension in the applicant's own DECISIONS.md.
