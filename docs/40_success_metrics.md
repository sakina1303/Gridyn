# Success metrics and reporting rules

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) defines denominators and units; [57_report_schema.md](57_report_schema.md) fixes provenance fields.

Report every metric by site, period, resolution, scenario, and baseline; show median/range across seeds and unfavorable cases.

| Type | Metric | Calculation / interpretation |
|---|---|---|
| Forecast | MAE, RMSE | Mean absolute/squared-root errors in kW on held-out intervals; MAPE only when target >0 and meaningful. |
| Solver | Runtime, optimality gap, feasible rate | Wall seconds, solver-reported gap, feasible validated incumbents / attempted valid inputs. |
| Physics | Constraint violations | Maximum and count of balance/SOC/rating/service residuals; hard violations target zero. |
| Uncertainty | Coverage, interval width, reliability calibration | Empirical fraction truth in stated intervals; predicted versus observed response success by bin. |
| Data efficiency | Envelope overstatement, abstention, value of measurement | `max(estimate−truth,0)` kW; abstentions / cases; change after added measurement. |
| Recommendation | Consistency, operator acceptance | Same inputs yield same action; later operator yes/no and reason, not a synthetic acceptance score. |
| Energy | Peak import | `max_t i_t` kW; reduction versus paired baseline. |
| Energy | Grid import/export and PV use | `Σ i_tΔt`, `Σe_tΔt`, `Σ(Gavail−u)Δt` kWh; PV utilization only with positive available PV. |
| Energy | Curtailment | `Σu_tΔt` kWh; reduction versus baseline. |
| Economics | Cost | Tariff-specific INR including applicable energy, demand and export terms; savings conditional on tariff and baseline. |
| Asset/service | Battery throughput, equivalent cycles, unmet EV/pump/comfort | Throughput kWh; cycles defined as discharge kWh/usable battery kWh, not health loss; service deficits separately. |
| Research | Reproducibility, robustness, generalization | Exact config/data hash and seed; performance across seasons/asset mixes; real-site holdout only if obtained. |

No fixed percentage improvement target is set before experiments. The decisive success criterion is **fewer overconfident flexibility promises at useful data burden** than conservative baselines, with zero hard-service violations in the model. A system that abstains on all cases also fails usefulness.
