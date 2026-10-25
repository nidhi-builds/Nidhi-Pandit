# Ridgeline weather checker design

Status: user-approved design implemented and evaluated on 2026-10-25. The execution ledger records justified refinements; measured results are in docs/validation-results.md. Applicant-owned submission tasks remain pending.

## Purpose and chosen approach

Help the network coordinator decide which observations can support the spring climate summary and where to send one technician for one hour. The checker must run on another pack of the same format. It must preserve real weather, explain its decisions, and expose uncertainty.

The user selected deterministic rules plus corroborating evidence, with no runtime AI. Alternatives considered: basic rules alone are simpler but miss plausible biases; runtime AI adds interpretive flexibility but has no demonstrated advantage here and complicates reproducibility. AI remains a development/review tool, documented through genuine chat exports.

This is a small offline analysis project. Use Python 3.11+, pandas, NumPy, Matplotlib, and the Python standard library; pytest for tests. Pin exact tested dependency versions during implementation. No backend server, database, frontend framework, paid services, network calls, training pipeline, or runtime LLM. Matplotlib produces embedded evidence figures; plain HTML/CSS supplies the report.

## Deliverables and scope

- `python checker.py <pack-folder>` writes `flags.csv`, `report.html`, `evidence.json`, and `review.csv` into the current working directory.
- `flags.csv` has exactly `station_id,channel,start_utc,end_utc,issue,action,note` in that order. Dates use `YYYY-MM-DD HH:MM`; actions are `exclude`, `correct`, or `keep`.
- `report.html` is the required network health report: one A4 page preferred, two pages maximum when printed. Screen-only expandable evidence may be longer.
- `evidence.json` and `review.csv` are auxiliary audit outputs, not extra columns or actions in `flags.csv`.
- Submit code, the supplied pack's generated flags/report, README, personally written DECISIONS.md, genuine AI logs, and a three-minute recording as required by the brief.
- The original datapack is private to this assignment. Never commit it, its extracted copies, or full raw-data replicas. Use synthetic fixtures in the public repository. Review evidence artifacts and chat exports for accidental full-pack disclosure.
- Do not compute a climate summary or interpolate missing weather. Do not claim an entire station is bad because one channel is affected. No automatic hardware-cause diagnosis or broad sensor recalibration.
- The programmer implements documented scientific calculations; the assignment's specific no-AI, by-hand solar-noon answer remains entirely the applicant's work.

## Final vocabulary: nine fault types

Subtypes live in evidence, not as additional issue categories. Channel and interval supply the affected scope.

| `issue` | Included subtypes | Decision policy |
|---|---|---|
| `missing_data` | absent records; missing or unparseable channel values | Exclude the unavailable scope; never invent replacements |
| `duplicate_data` | identical duplicates; conflicting duplicates; repeated blocks | Correct only verified duplicate copies; conflict goes to exclude/review; matching sequences alone do not prove replay |
| `clock_error` | fixed offset; abrupt jump; gradual clock drift | Correct only GPS-supported, unambiguous time mappings; otherwise exclude affected timed use or review |
| `location_mismatch` | installation coordinates disagree with reliable GPS | `channel=metadata, action=exclude`: withhold the installation coordinates pending verification; do not exclude weather values |
| `out_of_range` | definite domain violations | Exclude affected channel observations |
| `flatline` | sensor stuck despite evidence that it should respond | Exclude supported failures; retain ambiguity for review |
| `spike` | isolated excursion with return to baseline | Exclude only with corroboration; do not apply this generic rule to rain or circular wind direction |
| `sensor_bias` | additive step; multiplicative change; gradual drift; sunlight-dependent temperature bias | Exclude supported biased intervals; quantify bias for evidence, not automatic calibration |
| `rainfall_underresponse` | repeated absent or greatly reduced response during supported rain events | Exclude only supported events/intervals; uncertain local rain differences go to review |

`corroborated_weather_event` is a separate non-fault issue with action `keep`, used only for positively supported unusual events. Absence of a fault flag does not prove validity. Checks with insufficient evidence must say so.

Irradiance timing disagreement is evidence for `clock_error` or `sensor_bias`, not a tenth fault. Radiation-related temperature excess is a `sensor_bias` subtype. Invalid GPS messages are diagnostic evidence failures, not automatic weather faults. An invalid weather timestamp that cannot be placed in an interval belongs in diagnostics/review with its row identity, never a fabricated UTC range.

## Pipeline and ownership

1. **Load without alteration.** Read metadata, weather and GPS; retain relative source path, physical line number, original row order and raw timestamp. Reject missing required schema/files with a clear nonzero exit before writing new results. Weather numeric parsing failures become missing-value candidates, not crashes. Missing optional GPS or notes disable dependent checks and are disclosed.
2. **Audit records and GPS.** Detect duplicates before sorting or aggregating. Check NMEA checksums, fields and RMC validity; parse hemisphere-aware coordinates and GPS date/time. GGA alone does not provide a date. Bad checksums and invalid fixes cannot support correction. Maintain logger/file-order segmentation so a clock reset cannot silently join unrelated records.
3. **Establish analysis time.** Identify stable GPS/logger offset segments. Preserve raw time and corrected analysis time separately. Only apply supported mappings in memory; never rewrite source files. Exclude uncertain time segments from cross-station and solar comparisons.
4. **Run basic checks.** Identify missing intervals, missing values, domain failures and candidates for flatlines/spikes. Use each station's declared cadence, not a hardcoded ten minutes. Do not infer missing days outside a station's known operating span merely because another station has longer coverage.
5. **Build suitable comparisons.** Remove already unusable observations from reference fitting. Select at most three usable reference stations using distance, overlap and observed baseline agreement. Require two agreeing references for automated relational exclusions. Nearest is not necessarily suitable.
6. **Evaluate relationships and persistence.** Detect changes in residuals relative to normal relationships, and look for supporting cross-channel patterns. Do not compare raw station pressures for equality. Temperature comparisons distinguish solar day/night and compare similar light/wind conditions.
7. **Decide, consolidate and explain.** Produce deterministic actions from evidence requirements. Merge adjacent observations of the same fault/channel/action; never bridge an observed clean interval. A stronger explanation suppresses derivative duplicates: clock error before irradiance-timing symptom; flatline before generic bias; hard domain failure before spike.
8. **Render the report and audit outputs.** Stable ordering, templates populated with computed quantities, no unverified causal prose. Validated output is written atomically. Network calls are prohibited during checker execution.

## Relationship logic and initial detector settings

These are explicit engineering starting values, not published universal weather-quality limits. Tune on development fixtures and documented original-pack observations only, then freeze them before the final benchmark. Numerical changes require a reason and regression tests; never tune against final-test labels.

- **Baseline:** hourly median aggregates for continuous-channel reference fitting; retain native cadence for final flags. Require at least seven days of overlapping eligible data and 70% paired hourly coverage in that span. Use median/MAD residuals and hourly-change agreement, not equality of absolute measurements. Pressure references need hourly-change correlation >=0.7; temperature references >=0.5. Reference selection for other channels also requires their channel-specific controls to pass. If three references disagree substantially, do not vote through a fault; downgrade to review.
- **Baseline contamination:** fit candidate pre/post regimes separately; do not let an apparent post-change segment redefine the whole baseline. Exclude previously identified faults. A fault present for the entire pack may be unidentifiable; do not claim its detection without independent evidence. Refitting is limited to one exclusion/refit pass for predictable behaviour.
- **Implemented reference safety:** shared `reference.py` masks suspect and conflicting values before fitting. Basic spike/flatline corroboration requires seven eligible days of hourly-change agreement outside candidate intervals and may use all qualified peers; persistent bias selection remains capped at three. Short packs retain candidates for review. Two constant failed references cannot corroborate a spike.
- **Implemented replay safety:** equal values alone never authorize deletion across an unverified reset. A varied, fully matching earlier block additionally needs at least six valid GPS-date anchors; same-segment exact retransmissions remain correctable. Competing weather segments prevent a GPS correction unless their mapping is unique.
- **Hard ranges:** humidity outside [0,100], negative rain, negative mean wind, or wind direction outside [0,360] are domain failures. Accept 360 as equivalent to 0 for comparisons. Nonfinite/unparseable values are `missing_data`. Temperature/pressure extremes and small negative irradiance are screening evidence, not automatic exclusions based on invented universal limits.
- **Flatline:** exact repeated reported values for >=12 hours trigger a candidate in temperature, humidity, pressure or wind. Rain=0 and night-time irradiance=0 are normal. To exclude require persistence plus independent evidence of lost response; humidity at 100% remains review unless repeated dry-weather/context evidence rules out a plausible saturation episode. A constant GPS coordinate is not a flatline fault.
- **Spike:** isolated one/two-record excursions, return within two records, residual >6 robust scales, and adequate nonzero channel-specific noise floor. Initial scale floors: temperature 0.3 C, pressure 0.5 hPa, humidity 2 percentage points. Require two suitable references or an independent channel/domain contradiction before exclusion. Record final development-calibrated floors in configuration; zero MAD must never make every change a fault.
- **Sensor bias:** use persistent changes in hourly target-minus-reference residuals. Screen >=24-hour changes exceeding six pre-change robust scales and a channel floor. Development floor proposals: pressure 3 hPa, temperature 2 C, humidity 10 percentage points. Wind scale screen: >=1.4x or <=1/1.4x with adequate non-calm observations. Require >=48 usable hours on both sides of a step and agreement from two references. Fit gradual drift to daily residual medians over >=7 days and require agreement across independent halves. A shorter or unidentifiable drift stays review.
- **Radiation subtype:** target temperature excess must increase in high-light/low-wind conditions compared with its own pre-change relationship and suitable references. Initial bins: GHI >=400 W/m2 and wind <=5 km/h versus GHI <=20 W/m2. Require >=3 qualifying days, >=18 eligible hourly samples per comparison group, and a >=2 C increase in the conditional excess. Flag only contiguous affected observation intervals, not healthy nights between them. Missing or suspect light/wind channels disable automatic classification. Genuine local microclimate changes remain a limitation.
- **Rain:** define independent regional rain episodes separated by >=6 dry hours. Seek >=3 episodes with two suitable references each recording >=2 mm and the target <=10% of their median accumulation. This is a candidate, not proof: automated exclusion additionally needs temporal evidence of lost response (previous/recovered response in comparable events). Maintenance context can strengthen a human investigation but does not supply a runtime exclusion trigger. With uncertain onset, flag only supported episode intervals, not every dry day between them. Snow/freezing conditions and spatially isolated rain force review unless stronger evidence is available.
- **Clock:** at least six valid hourly RMC observations across >=5 hours; sustained logger-minus-GPS offset >60 seconds and within-segment MAD <=5 seconds support a fixed-offset candidate. Require an unambiguous file-order mapping into weather rows. Round a supported fixed offset to the nearest minute only when residuals are within five seconds and the mapping is unique. No interpolation across reset boundaries or extrapolation beyond supporting GPS intervals. For gradual drift, compare daily median offsets across >=3 days and require a consistent absolute trend >=60 seconds/day with total displacement >60 seconds; qualified benchmark drift is >=2 minutes/day. Confirmed drift without safe correction receives `exclude` for affected timed use over the GPS-supported span. Ambiguous row mapping goes to review. Automatic correction is limited to supported constant-offset segments in v1.
- **Location:** >=24 valid fixes spanning >=24 hours, persistent median horizontal mismatch >1 km, and 95% of fixes within 100 m of their median support a metadata discrepancy. Missing/poor fixes disable the decision. Do not automatically replace installation metadata from GPS alone. Do not use GPS altitude as an interchangeable installation-elevation reference.
- **Keep:** a candidate unusual pressure/temperature event can be retained when at least two suitable references show a coherent contemporaneous change, supporting channels are plausible, and no stronger integrity fault explains it. Other events can remain unclassified/review; a missing fault flag is not a blanket keep decision.
- **Notes:** quote applicable maintenance text and dates as supporting context; do not use station IDs, known fault dates, or keyword matches as fault triggers. V1 stores notes for human interpretation rather than attempting automated natural-language diagnosis. No human annotation file changes automated flags; the report may describe unresolved maintenance-backed concerns separately.

## Actions, time conventions and evidence

- A `correct` row is an instruction, not a modified data file. V1 corrects verified duplicate copies and GPS-supported fixed clock offsets only. It never guesses humidity, rain, pressure or wind replacements.
- Identical duplicates: retain the first source row and identify the redundant rows in evidence. A `duplicate_data/correct` interval means deduplicate, not delete every value at that timestamp. Conflicting duplicates: exclude only channels whose values conflict; record whether GPS explains the collision first.
- `start_utc`/`end_utc` are inclusive original logger timestamp labels for observed rows; notes explicitly identify a clock correction direction and offset. Internal provenance disambiguates repeated timestamps and reset segments. Metadata issues cover the observed evidence span. Missing-record intervals use the inferred expected analysis grid and declare that basis in the note. This avoids hiding bad raw labels behind corrected labels.
- Split intervals at every backward clock reset and monotonic source segment; never emit `start_utc > end_utc`. Where labels repeat, the CSV note states the time basis and exact source file/row ranges so a CSV-only reader can identify the records. Split disjoint row ranges when needed; sidecar-only disambiguation is insufficient.
- Every output flag has a deterministic sidecar entry keyed by its stable CSV row ordinal. Include source row references, subtype, rule/config version, time basis, measurements, thresholds, reference IDs, eligible sample counts, evidence limitations and action rationale.
- `review.csv` columns: `station_id,channel,start_utc,end_utc,candidate_issue,reason,needed_evidence`. Leave times blank only for truly unplaceable records; include their provenance in evidence.
- Audit output includes per-channel evaluated/unevaluated coverage and check-disable reasons. Abstention does not inflate recall or hide missing capability.
- Publication-safe evidence contains bounded supporting snippets/statistics and figures, not the complete input tables. Input and configuration hashes support reproducibility.

## Frontend: one offline HTML report

No separate application. The command produces a self-contained `report.html`, openable directly in a browser.

The printed report contains:
1. Title, observed date coverage, brief usability recommendation and unresolved limitations.
2. Station/channel matrix with one row per discovered station (eight in the supplied pack): usable under completed checks, exclude, correct-before-use, or needs review. Text/symbols accompany colour. Mixed intervals are not flattened into a misleading all-good/all-bad status. For a large unseen pack, print a condensed summary and retain all station rows on screen; the submission's <=2-page gate is verified on the supplied pack.
3. The most consequential affected channels and time ranges, with plain-language actions and one or two compact evidence figures.
4. The technician visit recommendation: one station, first check, tasks fitting one hour, runner-up and the reason for prioritization.

Screen-only `<details>` panels show the full flags table, per-flag evidence, review candidates, disabled checks and a link to `flags.csv`. The print stylesheet omits those panels and interactive controls. Escape all input text; use no external assets. Keyboard-native controls and readable grayscale printing are required.

Generate a technician shortlist from ongoing supported faults and affected channel-hours, with explicit uncertainty. Do not manufacture a precise risk score. The final one-hour visit recommendation and comparison with the runner-up are human-authored in optional `report_context.json` in the current working directory. It contains `input_fingerprint`, `station_id`, `first_check`, `tasks`, `runner_up`, and `reason`. The fingerprint is SHA-256 of the canonical sorted relative-input-path/content-hash map (UTF-8 compact JSON). Accept context only if the fingerprint matches the loaded pack and station IDs exist; absent, invalid or stale context displays 'visit recommendation pending review' and a diagnostic. This prevents an old recommendation leaking onto an unseen pack. Release on the supplied pack requires a completed recommendation. Do not treat all measured variables as equally valuable by assumption.

Report availability counts use disjoint observation/channel states. Metadata discrepancies and `keep` rows do not remove weather values. Missing intervals and duplicate extra rows have separate counts; never double-count them as observed bad cells. Multi-fault overlap is counted once per affected observation/channel.

## Evaluation, rollout and unresolved status

The exact benchmark rules, denominators and pass gates are in `docs/EVALUATION.md`. The implementation sequence is in `docs/superpowers/plans/2026-10-24-weather-checker.md`.

Original-pack labels were evidence-reviewed independently of relational detector output. Unknown cases stay unknown. Synthetic held-out results establish performance on the sampled cases; they do not prove the entire target envelope or universal meteorological accuracy. See the precise benchmark footprint and measured results.

Scope deliberately omits learned anomaly models, automatic sensor recalibration, a hosted dashboard and generalized understanding of maintenance prose. The main expected effort is investigation and evaluation, not frontend engineering. If gates fail, fix the detector or explicitly renegotiate scope; never claim passage or silently weaken the benchmark.

## Primary technical references

- GPS fields and validity: [Trimble RMC](https://receiverhelp.trimble.com/oem-gnss/nmea0183-messages-rmc.html), [GGA](https://receiverhelp.trimble.com/oem-gnss/nmea0183-messages-gga.html), [common message elements](https://receiverhelp.trimble.com/alloy-gnss/en-us/nmea0183-messages-common-message-elements.html).
- Solar context implementation: [NOAA general solar calculations](https://gml.noaa.gov/grad/solcalc/solareqns.PDF). Use a small documented helper and independently sourced fixtures for dates/sites other than the assignment's by-hand question. No solar-noon answer for that question is generated in the documentation.
- The numeric detection settings above are project proposals, not thresholds attributed to those references.
