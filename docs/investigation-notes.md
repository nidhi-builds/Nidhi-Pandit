# Original-pack investigation notes

Status: initial analyst evidence review, frozen before relationship detectors. These are not authoritative ground-truth labels or a claimed overall accuracy score. Private full-series figures and ledger remain in ignored `private/`.

All seven channels at all eight stations were inspected as full-series plots, with record counts, missing values, constant runs, GPS offsets and station coordinates checked. No numeric cells are missing in the supplied files; missing records and duplicates remain separate questions.

## Directly supported observations

- S03 temperature is exactly 6.5 C for 481 samples from 18 March 06:00 to 21 March 14:00 while other channels/weather vary. Four isolated -40/85 C excursions occur outside that run and immediately return toward the surrounding series. Exact constancy and transient shape support investigation independently of notebook dates.
- S05 humidity exceeds 100% in 451 observations between 7 March 12:10 and 11 March 00:00. These are domain violations, not legitimate saturation. Reliable GPS coordinates differ from the installation coordinates by approximately 20.45 km. The correct installation position still needs verification.
- S06 GPS/logger offsets change from approximately 0-2 seconds to approximately -21,600 seconds following the reboot period. Repeated logger labels must be treated as potential clock collisions, not discarded as retransmissions.
- S08 has an interior delivery gap and 144 repeated timestamp labels. A full duplicate-content comparison is required before recommending deduplication.

## Relational hypotheses to test, not assume

- S02 pressure relative to S03 changes by 6.5 hPa in one interval at 21 March 17:20. The next-largest relative steps are much smaller. A persistent offset and additional references must support the final decision; the replacement note is corroboration, not the detector.
- S07 wind speeds drop in scale around the anemometer replacement period. Natural weather can also change wind; compare its own previous wind relationship with multiple suitable stations.
- S04 daytime temperature and rainfall behaviour warrant further evidence. Sunshine-related excess, local weather, clogging and delayed release are competing explanations. Dry neighbours alone cannot establish a blocked gauge.
- S01's lower pressure and colder temperatures are compatible with its elevation; their absolute disagreement with lower stations is not a fault.

The independent ledger contains all 56 station/channel baseline review rows plus targeted cases. Confirmed labels are restricted to directly observed defects; causal and ambiguous relational claims remain uncertain until corroborated.
