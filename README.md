[Your full name]
[Your email]
[Three-minute video link]
Run: python checker.py <pack-folder>

# Ridgeline weather network checker

**Status: design and implementation plan only. The command above is planned and is not runnable yet. No checker results or accuracy claims have been produced.**

An offline deterministic checker to help decide which station measurements are usable and where one volunteer technician should visit. No runtime AI or external API is planned.

- [Design and final fault vocabulary](docs/superpowers/specs/2026-10-24-weather-checker-design.md)
- [Stage-gated implementation plan](docs/superpowers/plans/2026-10-24-weather-checker.md)
- [Exact evaluation contract](docs/EVALUATION.md)
- [Applicant-owned decisions](DECISIONS.md)
- [AI-log export instructions](ai_logs/README.md)

## Planned usage

Install the pinned requirements once implementation supplies them. Extract the private pack outside tracked source paths. Run the command from the directory where outputs are wanted. The input folder contains `stations.csv`, `data/*.csv`, optional `gps/*.nmea` and optional maintenance notes.

Planned outputs: required `flags.csv` and printable `report.html`; auxiliary `evidence.json` and `review.csv`. Raw inputs are preserved. Uncertain events remain visible and do not acquire a fabricated final action.

## Planned checks

Missing data, duplicate data, clock errors, location mismatch, impossible values, flatlines, spikes, sensor bias and rainfall underresponse. Sensor bias includes additive, multiplicative, gradual and sunlight-dependent cases. Relationships account for normal station differences; absence of a flag does not prove validity. Positively supported unusual weather may receive a `keep` flag.

## Limitations and unfinished work

All implementation and testing remain pending. The original pack has no supplied ground-truth labels. The final README will document actual checks, measured validation results, disabled checks and remaining uncertainty. Automatic correction will be limited to verified duplicate removal and supported constant clock offsets.

Do not commit the datapack or raw extracted copies. Replace the four opening placeholders with real applicant details before submission. Preserve the assignment's required personal authorship of DECISIONS.md and the no-code/no-AI calculation.
