# Minimum data experiments

## Research question

How do interval resolution, history length, missingness, and asset-meter coverage change error in the **decision** (delivered flexible kW/service), not only forecast MAE? A numeric minimum will be learned experimentally rather than asserted in advance.

## Reference and ablations

Use a full-information synthetic truth set with known asset dispatch plus, if obtained, consented real site data. Split chronologically by season; never train on the test period. Reference: 15 minute load/PV/asset observations, confirmed ratings and schedules. Ablate one factor at a time and then selected interactions: hourly versus 30/15 minute; 30/90/180/365 day histories; 5/20/40% missing values in random points and contiguous outages; no PV meter; missing SOC; unknown EV sessions; biased meter ±2/5%; incorrect battery capacity/efficiency; stale tariff. Repeat across seasons and asset mixes with fixed seeds.

For each dataset, run the identical readiness → forecast → flexibility → schedule pipeline. Compare against the full-information feasible response on the same hidden realization. Primary metrics: conservative-envelope coverage, overstatement rate and size, delivered kW for 1/2/4 hour windows, critical/service violations, regret against full-information decision, and width of feasible interval. Secondary: forecast MAE/RMSE, runtime, abstention rate. A system that abstains safely should be distinguished from one that makes a wrong confident claim.

## Questions and expected tests

- **Hourly only:** can estimate coarse energy shifts; test whether peak response overstatement rises when 15 minute spikes are hidden.
- **PV without meter:** capacity/weather model may bound PV, but renewable utilization cannot be verified; compare bounds against hidden PV trace.
- **Unknown SOC:** range over possible SOC; test whether any nonzero reliable discharge is defensible. Do not infer SOC from net site import alone without identifying battery power.
- **30 days versus 6/12 months:** evaluate seasonal test degradation; report each climate/season separately.
- **Value of a measurement:** add one meter/field back at a time; rank reduction in overstatement and interval width per measurement burden, with confidence intervals across replicate sites.

Pre-register the grid of ablations, seeds, baselines, and threshold criteria before looking at results. Failure: no stable threshold across site types or no performance advantage over a conservative rule. Then report conditional minimums rather than a universal number.
