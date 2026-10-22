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
