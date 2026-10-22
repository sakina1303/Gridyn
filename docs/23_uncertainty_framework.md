# Uncertainty framework

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) and [50_response_envelope.md](50_response_envelope.md) define the reported response and tested reliability. Scenario fractions are not field probabilities.

**Choice for prototype:** deterministic stress scenarios first; once enough held-out history exists, empirical forecast residual scenarios and prediction intervals. Evaluate schedules out of sample with a fixed random seed and rolling time split. Do not present a probability when data cannot support calibration.

| Source | Representation and needed data | Flexibility/decision effect | User display |
|---|---|---|---|
| Solar/weather | Clear/cloudy traces or residuals conditional on hour/season; PV or irradiance/weather history | Surplus and battery charge opportunity shrink | Low/central/high PV traces and assumption |
| Site load | Historical residuals by hour/day or ± stress bands; interval import and PV separation | Peak reduction requirement and connection headroom change | Demand band, worst tested peak |
| Battery initial SOC/ratings | Metered SOC or bounded interval; nameplate/usable capacity/efficiency | Changes discharge duration and reserve | SOC source and bound |
| EV arrivals/departures/energy | Scenario sets from bookings or observed sessions | Charging window may collapse | Missed-departure risk and service shortfall |
| HVAC and pump availability | Occupancy, temperature, tank/operating schedule scenarios | Comfort/service constraints tighten | Constraint range and unavailable times |
| Missing/noisy measurements | Missing blocks, time shifts, additive noise and meter bias injected into known-good traces | Can overstate feasible response | Readiness warning and sensitivity |
| Incorrect asset parameters | Rated versus derated efficiency, capacity and ramp | Technical envelope overstated | Parameter range and binding constraint |
| Tariff changes | Versioned state/category schedules and alternative scenarios | Changes economic recommendation, not physical flexibility | Tariff source/version; bill comparison conditional |
| User behavior | Acceptance/override scenarios | Delivered response less than modeled | Advisory versus realized response |

## Method decision

| Method | Use now? | Reason |
|---|---|---|
| Deterministic scenarios | Yes | Auditable and works without historical distributions; no probability claim. |
| Monte Carlo | Limited, later in MVP if seeded residual library exists | Samples interacting uncertainties, but quality depends on joint distributions. |
| Prediction intervals / conformal | Research experiment after adequate held-out history | Test empirical coverage under time shift; coverage can fail under distribution shift. |
| Quantile regression | Compare if interval data support it | More data and tuning than simple residual intervals. |
| Robust optimization | One small stress-set experiment | Guarantees only for the defined uncertainty set, may over-constrain. |
| Stochastic optimization | Post-MVP | Scenario explosion and probability assumptions are not justified initially. |

## Reliability protocol

Train/calibrate/test strictly in time order. For each proposed response `q,W`, replay it across `N` held-out or documented synthetic realizations with the same operational constraints. Report `successes/N`, binomial interval when iid assumptions are defensible, sample provenance, and worst service deficit. If all traces are synthetic, label the reliability **simulation conditional**. Avoid arbitrary score labels such as “high confidence” without thresholds and calibration. Optimization should compare nominal schedule with a stress-safe schedule and expose the cost/reliability tradeoff.
