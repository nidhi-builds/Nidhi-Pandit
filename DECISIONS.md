# My investigation decisions

## 1. The visit

I would spend the hour at S02, North Mesa School, and take a calibrated portable pressure reference. The checker found that S02's pressure relationship changed persistently: its 48-hour pre/post shifts were about 6.7 hPa relative to S03 and 6.6 hPa relative to S04. That agreement makes this a stronger first visit than S07's wind concern, where local exposure can naturally make station-to-station readings differ.

I would first inspect the replacement board, units, vent and configuration. Then I would compare simultaneous S02 and reference readings, record whether any offset is stable, and check the documented calibration procedure. I would only adjust the sensor if the reference readings and manufacturer procedure support it, and would keep before/after readings and configuration details. This is a proposed priority, not a diagnosis that the board is definitely faulty. S07 remains a follow-up, and I would not make a pressure adjustment without the reference instrument.

## 2. My least certain call

The S05 `location_mismatch` flag is the call I would verify most carefully. Valid GPS fixes cluster about 20.45 km from the registered installation coordinates, which supports withholding those coordinates until they are checked. However, the checker cannot tell from GPS alone whether the station was moved, the registered coordinates are stale, or the GPS installation/location record is wrong. I would ask for the current site coordinates and installation or relocation record. That would resolve whether this is a metadata correction or a genuine location problem; it does not by itself make S05's weather readings faulty.

## 3. Where I chose not to use AI at runtime

While choosing the system approach, AI suggested adding AI to interpret findings and provide the final action. I decided that this did not give the checker a useful advantage: the supported actions can be tied directly to measured rules, source rows and thresholds, while an AI-generated interpretation could be harder to reproduce and audit. I steered the design toward measurable evaluation gates and a staged plan in which later work depended on the earlier gate passing. I also wanted the comparisons to account for normal station relationships and cross-channel context, so natural differences between stations would not be mistaken for faults.

This is my recollection of the design discussion, not a verbatim quotation. The saved conversation is now in `ai_logs/conversation.md`; I still need to select one or two checked quotations before submission. I will not invent a quote.

## 4. If this ran unattended on 500 stations

I would keep the core detector deterministic, but move from one local batch run to a scheduled pipeline with versioned inputs and rules, per-station coverage monitoring, durable evidence storage and alerts for failed or incomplete runs. I would measure processing time and memory on representative packs before claiming the system can handle 500 stations. I would expand held-out tests across station counts, climates, elevations, cadences and fault combinations, and monitor the review rate and false alarms after deployment.

I would drop any rule that depends on a particular station ID, date or maintenance note. I would not automate sensor recalibration, extrapolate clock corrections beyond GPS support, or turn weak peer comparisons into exclusions. Those cases should remain review items until independent evidence is available. A screened reading would still mean only that the available checks found no supported fault.

## 5. By hand: solar noon at S04 on 20 March 2025

**Applicant completion required:** I will estimate this independently without code or AI, show the longitude/time-zone and equation-of-time working, and state the estimated local clock time here. I will also explain that solar noon is useful as a sanity check for the timing of sunlight readings, not as proof that the sensor is calibrated. This answer is intentionally left for my own calculation.
