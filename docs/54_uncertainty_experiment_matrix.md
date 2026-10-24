# Uncertainty experiment matrix

Each row uses a paired synthetic hidden truth and corrupted/limited observation from [48](48_synthetic_dataset_spec.md). The model never sees truth at decision time. Evaluate a committed 1/2/4 h response against truth; report overstatement, success/service, decision regret and abstention. Nominal confidence is `unknown` unless calibrated on a separate historical split.

| Factor / levels | Truth and observed data | Model decision | Error/confidence evaluation | Expected failure mode |
|---|---|---|---|---|
| PV forecast error: clear/cloudy mismatch | True cloud trace; persistence/weather forecast with residual shift | Battery/EV solar-hour schedule | PV MAE, curtailed kWh, delivered down/up kW; interval coverage | Charge plan lacks PV |
| Load forecast error: peak timing ±1–3 h | True demand peak; shifted forecast | Peak-reduction schedule | Peak regret and service; forecast interval coverage | Response at wrong hour |
| Missing values: 5/20/40%, points/blocks | Complete trace; observation mask | Envelope or abstention | Overstatement, width, false-confidence rate | Gap hides peak/asset use |
| Noise/bias: ±2/5%, outliers | Clean meter truth; noisy/biased records | Readiness and forecast | Detection precision/recall on injected faults | System accepts biased rating |
| Initial SOC unknown/range | Fixed hidden SOC; absent/stale SOC | Battery response or abstention | SOC feasibility across scenarios | Over-discharge |
| EV arrival/departure uncertainty | Hidden sessions; coarse booking | Charging shift | EV energy by departure, success fraction | Missed departure service |
| Weather/temperature uncertainty | Hidden temperature; forecast perturbation | HVAC/PV action | Comfort violation, PV forecast error | Cooling shifted unsafely |
| Asset availability/rating uncertainty | Hidden derating/outage; stale metadata | Aggregate envelope | Delivered kW and binding constraints | Double count or unavailable resource |
| Tariff uncertainty | Physical truth unchanged; stale/alternative tariff | Cost schedule | Cost regret under applicable tariff; no physical reliability change | Wrong economic recommendation |

Run one-factor sweeps first, then high-risk interactions (PV+SOC, EV+tariff, missingness+resolution). Each factor has at least three severity levels plus clean control and multiple fixed seeds. Calibrate intervals on train/calibration periods only; report held-out empirical coverage by season. Failure criterion: a confident firm response with critical/service violation or repeated overstatement beyond declared tolerance. Stress-only results are labeled conditional.

## Current execution boundary

Run `PYTHONPATH=backend/src .venv/bin/python scripts/run_full_uncertainty_matrix.py --output-dir .local/uncertainty_matrix` to create a combined audit with row-level reasons. The declared synthetic physical replay covers both import-response directions, 1/2/4-hour commitments, three seeds, clean control, three PV levels, high/low load levels, ±1/2/3-hour peak shifts, low/high initial SOC, EV arrival/departure/service, pump runtime, battery derating and PV+SOC interactions. It retains overstatement, baseline failures, candidate failures, recovery energy and physical-balance residuals. The paired observation protocol covers missingness, bias, noise, a block gap, 30-minute resolution and missingness+resolution interaction. These are **model stresses**, not sampled field reliability. The fixed physical schedule is not an optimized forecast-issued decision; its delivered counts cannot be interpreted as site performance rates.

Thermal comfort and tariff/EV cost interaction are explicitly `not_evaluable`: the canonical HVAC model has power/window bounds but no thermal-state response, and no verified applicable tariff is supplied. The observation protocol's missingness+resolution variant is an abstention under its strict previous-day training rule. A more permissive forecast model and site-calibrated faults would need a separate pre-registered study. Seasonal held-out coverage, decision regret for every factor, noise detection precision/recall against verified faults, and field response reliability are not established.

The executable studies cover different parts of this matrix. A public observed-data benchmark uses the [I-BLEND Academic building meter](https://springernature.figshare.com/articles/dataset/Energy_dataset_of_IIITD/6007637) (CC0, IIIT Delhi). Its 41-day, one-minute W sample is strictly aggregated into complete 15-minute kW intervals. Seven later complete days are held out for issue-time forecasting; clean and three-seed severity sweeps cover random missingness (5/20/40%), signed bias (2/5/10%), noise (2/5/10% of mean load), outliers (1/3/5%), and 1/4/12-interval gaps. The reproducible command is `PYTHONPATH=backend/src .venv/bin/python scripts/run_public_iblend_benchmark.py`. Results are **observed building mains forecast diagnostics under injected synthetic perturbations**. The source is one building meter, not verified site import or an asset-service trace.

| Matrix factor | Current executable evidence | Still needed for the stated matrix outcome |
|---|---|---|
| PV forecast error | Synthetic PV stress replay and forecast-decision study | Matched observed site PV plus load, availability/curtailment channel, chronological forecast coverage |
| Load forecast error / timing | Public observed building-load issue-time forecast error and peak error; synthetic decision regret | Whole-site import and asset-service logs for realized flexibility decision regret |
| Missing values | Public observed-load injection with abstention; paired synthetic envelope studies | Field missingness mechanism, calibrated response overstatement and interval coverage |
| Noise, bias, outliers | Public observed-load injection and forecast error; synthetic observation stress protocol | Meter fault labels and detection precision/recall against verified faults |
| Initial SOC | Declared synthetic low-SOC schedule replay | Timestamped battery SOC and AC power, initial-state uncertainty calibration |
| EV timing | Synthetic service constraints and required-energy stresses | Observed arrivals/departures and energy delivered by departure |
| Weather / temperature | Synthetic PV/weather scenarios; conservative HVAC power bounds | Measured indoor comfort and weather forecast error; no comfort validation yet |
| Asset availability | Declared synthetic battery derating replay | Availability logs, outages, ratings and service delivery |
| Tariff | Physical simulation stays tariff independent | Verified applicable tariff order, category and time-effective bill rules before any cost-regret claim |

The public benchmark does not close the real-site pilot gate. Statistical flexibility reliability, seasonal interval coverage, measured savings and operator acceptance remain **Unknown**. Do not interpret the repeated perturbation seeds as independent observed days; the clean control uses seven distinct held-out days.
