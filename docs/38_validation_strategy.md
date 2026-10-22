# Validation strategy

## Level 1 — mathematical correctness

Property and example tests for kW↔kWh conversion, every-timestep power balance, SOC equation/limits, efficiency, no simultaneous battery/grid directions, EV/pump service, critical load, and aggregate envelope feasibility. Independently recompute residuals from solver output; test infeasible inputs and solver timeouts. No displayed recommendation until checks pass.

## Level 2 — simulation and research validity

Generator checks: PV zero at night, bounded by rating, realistic calendar and cloud structure, no hidden truth leakage into observed inputs. Compare no-action, rule, and optimized strategy on identical hidden traces. Run repeated seeds and seasonal profiles. Forecast models use rolling-origin splits. Verify that interval coverage and flexibility reliability are calibrated where claimed; report failure rates, not just averages. Data ablations must alter only the intended observation channel.

## Level 3 — possible real-world validation

With consented data: reconcile meter totals with bills/asset readings, evaluate one-step forecasts, estimate flexibility against known operator schedules, then shadow-run recommendations without actuation. A true causal flexibility impact requires a defensible counterfactual or controlled trial; historical replay alone does not prove realized savings or response. If no real data are obtained, only Levels 1–2 can pass, and external validity remains unknown.

Acceptance gates: physical residual within documented numerical tolerance, zero hard-constraint violations, reproducible runs, forecast/baseline comparison, calibrated or explicitly unknown reliability, and no unsupported grid/carbon claims. Record software versions, solver termination and gap, source datasets, and failed cases.
