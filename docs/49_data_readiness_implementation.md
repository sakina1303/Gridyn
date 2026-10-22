# Data readiness algorithms

Readiness maps source quality to *claims*, not one global score. States: `usable`, `usable_with_limitations`, `insufficient`, `invalid`. Map older [24](24_data_readiness.md) levels as: prospective/retrospective may be usable for their specified claim; bounded → usable with limitations; blocked → insufficient; invalid is a new ingestion state. Thresholds below are **provisional engineering gates**, to be tuned using [25](25_minimum_data_experiments.md), not empirical minimum-data findings.

| Check / formula | Provisional trigger and severity | Interpretation / downstream effect |
|---|---|---|
| Coverage `valid_expected_intervals / expected_intervals` | `<0.80` insufficient for historical forecast; `<0.95` strong warning; **any** missing interval prevents a verified full-period peak claim unless an external billing peak is available | Gaps bias peaks; use scenario bounds or abstain |
| Missingness `missing/expected`, longest gap | `>20%` insufficient; gap `>4Δ` in response window blocks measured deliverability | Record random versus block missingness; never silently interpolate response event |
| Resolution `median(end−start)`, jitter | Unsupported interval or mixed resolution without declared conversion → invalid; 60 min blocks 15 min peak claim | Energy-preserving resample only to coarser resolution |
| Timestamp duplicates/overlap | Any unresolved duplicate or overlap → invalid affected series | Reject ambiguous aggregation; require offset for DST conflict |
| Range | Negative gross import/export/PV/load, SOC outside tolerance, efficiency outside `(0,1]` → invalid | Physical inconsistency; no analysis on bad intervals |
| Outliers | Robust deviation flag, e.g. `|x−median(hour peer)|>5×MAD` when MAD>0; never auto-delete | Warning for investigation; retain raw value and quality flag |
| Unit/sign consistency | Unknown unit/sign or kWh/kW mismatch → invalid | Require explicit conversion and provenance |
| Metadata completeness | Missing battery rating/SOC/efficiency or EV due/window blocks corresponding firm asset response | Other assets may remain assessable |
| Historical duration | `<30 d` forecast calibration unavailable; 30/180/365 d are experimental bands | Do not claim seasonal reliability from short history |
| Cross-signal balance | `|grid+PV+battery−load|>max(2 kW,0.02×site rating)` sustained for ≥4 intervals → warning/investigate | May be meter timing or unmodeled load; do not force equality by editing data |

Quality report stores numerator/denominator, intervals, severity, source, conversion, and impacted claims. Claim matrix: physical nameplate bound needs ratings/windows; technical battery response needs initial SOC and efficiency; measured PV utilization needs PV meter; tariff saving needs applicable tariff; 15 minute peak needs 15 minute data; calibrated reliability needs held-out events/scenarios of justified provenance. `Usable` never means physically controllable. Fallbacks are explicit engineering-bound scenarios, lower-resolution claims, or abstention. For every failure, suggest a concrete additional measurement.
