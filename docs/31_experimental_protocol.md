# Experimental protocol

Register simulator version, parameters, seeds, asset mix, tariff source, horizon, train/calibration/test dates, solver/version/gap, and exclusions. Use at least several seasonal synthetic weeks, not one cherry-picked day. Compare paired runs on identical hidden realizations and initial conditions. No real-world impact claim without real data and a credible counterfactual. Plots always include units and baseline.

| # / hypothesis | Dataset and methods | Metrics / visualization | Failure condition |
|---|---|---|---|
| 1. Optimization beats rule/no action on chosen objective | Full-data synthetic; A/B/C paired | Objective, peak, service; schedule overlay | No material gain or service harm |
| 2. Forecast error changes decisions | Perfect versus persistence/ML on held-out truth | Regret, violations, error band plot | ML not better than persistence |
| 3. Missing data widens reliable envelope or triggers abstention | Inject missing blocks into same traces | Overstatement, width, abstention curve | Confident wrong estimates |
| 4. Hourly hides some 15 minute peaks | Aggregate full truth, then replan | Peak error and response feasibility by resolution | No consistent difference; report that |
| 5. More battery is not always valuable | 0/100/200/400 kWh, same demand/PV | Marginal cost/peak gain and cycles | Gains depend on contrived tariff only |
| 6. More PV changes curtailment and shifts | 0/50/100/200 kW | Utilization/curtailment curves | No robustness across weather |
| 7. Asset availability limits response | Tight/medium/wide EV/HVAC/pump windows | Feasible kW-duration frontier | Model ignores service/comfort |
| 8. Tariff structure changes economic optimum | Flat and versioned ToD scenario | Cost and physical metric split | Savings claimed without tariff basis |
| 9. Uncertainty-aware schedule trades gain for reliability | Low/medium/high forecast/arrival error | Success fraction versus cost frontier | No reliability gain or gross overconservatism |
| 10. Coordination adds beyond single assets | Battery only, loads only, jointly optimized | Incremental outcome and rebound plot | Joint result equals independent sum incorrectly |

For all ten: baseline is the no-new-action trace plus a transparent rule where relevant; data are synthetic until a consented dataset is acquired. Expected results above are **hypotheses**, never promised outcomes. Each plot includes failed runs. Reproduce via saved config, deterministic seed, dataset checksum, and one command documented when implementation begins. Repeat over multiple seeds and report median/range; use paired bootstrap intervals only if sample count supports them. Publish negative results.
