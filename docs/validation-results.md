# Validation results

Status: NOT RUN. The checker has not been implemented. Targets are defined in [EVALUATION.md](EVALUATION.md); none is claimed as achieved.

| Release gate | Measured result | Status |
|---|---|---|
| G1: contract, reproducibility, input preservation | Not measured | Pending |
| G2: fault precision and recall by subtype | Not measured | Pending |
| G3: preservation of good observations | Not measured | Pending |
| G4: boundaries, action correctness, evidence | Not measured | Pending |
| G5: original-pack audit and submission | Not measured | Pending |

At implementation time record the code revision, pinned environment, detector configuration hash, input fingerprint and development/final-test manifests. For each subtype record TP/FP/FN, precision/recall, independent parent-episode count and interval count. Record boundary errors, known-good loss and corrections separately.

Original-pack findings must identify the reviewed labelled subset, unresolved cases and any missed confirmed events. Do not present these as an authoritative overall accuracy score. Preserve failed benchmark runs and explain any later changes.
