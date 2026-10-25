[Your full name]
[Your email]
[Three-minute video link]
Run: python checker.py <pack-folder>

# Ridgeline weather network checker

Offline deterministic investigation of a weather-network pack. Reads local files, preserves the originals, and writes interval decisions with source-row evidence. No runtime AI or network access is used.

Use Python 3.11 or later. Install the pinned dependencies once:

```powershell
python -m pip install -r requirements.txt
python checker.py "path/to/extracted-pack"
```

The pack must contain `stations.csv` and the declared stations' `data/*.csv`. GPS files and maintenance notes are optional; absent evidence disables dependent checks visibly. Logging cadence must be positive whole minutes, matching the timestamp format.

Run from the directory where you want the outputs. The command can also be called by its absolute script path from another directory.

- [Design and final fault vocabulary](docs/superpowers/specs/2026-10-24-weather-checker-design.md)
- [Stage-gated implementation plan](docs/superpowers/plans/2026-10-24-weather-checker.md)
- [Exact evaluation contract](docs/EVALUATION.md)
- [Applicant-owned decisions](DECISIONS.md)
- [AI-log export instructions](ai_logs/README.md)

## Outputs and actions

- `flags.csv`: exactly `station_id,channel,start_utc,end_utc,issue,action,note`; one row per consolidated supported event.
- `report.html`: self-contained coordinator report, printable on A4, with expandable evidence on screen.
- `evidence.json`: input/rule fingerprints, quantities, thresholds, references and exact physical source-row identities for flags and reviews. Header is row 1; first data row is row 2.
- `review.csv`: uncertain cases needing additional evidence. These are not silently treated as valid data.

`exclude` applies only to the named channel and interval; metadata exclusion withholds coordinates, not weather. `correct` gives an explicit operation: verified deduplication or a GPS-supported fixed clock offset. It does not rewrite the input. `keep` is reserved for positively corroborated unusual weather; no flag does not mean certified good.

Intervals are inclusive original logger labels, except missing-record flags explicitly identified as an expected analysis grid. Clock/reset instructions name source row ranges to disambiguate repeated labels. Missing timestamps stay in review with source rows. No missing weather is interpolated and no sensor calibration is guessed.

Optional `report_context.json` in the working directory holds a reviewed visit recommendation. Its input fingerprint and station IDs must match the pack; otherwise the report shows a pending recommendation. The included S02 recommendation is a proposal for applicant review.

## Checks

Nine issues: `missing_data`, `duplicate_data`, `clock_error`, `location_mismatch`, `out_of_range`, `flatline`, `spike`, `sensor_bias`, `rainfall_underresponse`. Bias subtypes cover additive, multiplicative, gradual and sunlight-dependent departures.

The checker validates GPS checksums/status, time and position; audits cadence, gaps and duplicate identities; screens definite domains, lost response and isolated excursions; and compares baseline-qualified station relationships. Temperature context distinguishes light/wind conditions. Rain checks require repeated regional events and evidence of prior/recovered response. Ambiguous clock resets never authorize deletion merely because values are equal. Varied replay blocks need additional valid GPS-date support.

Two trustworthy references and at least seven days of eligible baseline agreement are required for automatic basic relational corroboration. Reference fitting removes suspect/conflicting measurements. The bias model uses the first seven eligible baseline days; a fault present throughout that baseline can be unidentifiable. Maintenance prose supports human investigation and never hardcodes a fault date into the detector.

## Tests and measured validation

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The full suite includes independent synthetic development and locked final cases and takes several minutes. A quick core run is:

```powershell
python -m pytest -q --ignore=tests/test_development.py --ignore=tests/test_benchmark.py
```

See [validation results](docs/validation-results.md) for measured scores and gate status, and [evaluation definitions](docs/EVALUATION.md) for exact denominators, test envelopes and limits. Repeating the frozen final suite is regression checking, not a fresh blind evaluation.

The original pack has no supplied authoritative labels. Its evidence audit is reported separately from known-answer synthetic metrics. Local weather, an unreliable baseline and weak spatial comparisons can prevent a defensible decision. Review and limited-assessment indicators are part of the result.

## Applicant-owned submission work

Replace the opening identity/video placeholders, review the proposed technician visit, write DECISIONS.md personally (including the independent no-code/no-AI calculation), and add actual complete AI-chat exports. Do not commit the datapack or extracted raw copies. Follow the invitation deadline and repository naming/submission rules.
