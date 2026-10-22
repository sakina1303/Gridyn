# Scenario laboratory

**Implementation authority:** [52_baseline_hierarchy.md](52_baseline_hierarchy.md) defines information sets; [56_experiment_runner.md](56_experiment_runner.md) distinguishes an experiment protocol from one immutable scenario.

A scenario is immutable configuration plus dataset reference, baseline ID, solver/model versions, and seed. Editable inputs: PV AC capacity, battery usable kWh/power/efficiency, EV sessions and chargers, HVAC/pump windows and comfort/service, critical load, import/export cap, weather profile, tariff schedule, forecast error/stress set, and data-quality ablation. Validate units, nonnegative ratings, feasible windows, tariff dates, and compatible timestep before a run.

Every scenario runs on the same truth trace when compared. Results include grid import/export kWh, peak kW, tariff conditional cost INR, PV available/used/curtailed kWh, battery throughput/equivalent cycles under a stated definition, feasible and tested reliable flexibility by window, EV/pump/comfort deficits, hard-constraint residuals, and uncertainty range. `Confidence` is not a decorative percentage: show scenario success fraction or calibrated interval only when justified; otherwise label `not calibrated`.

Default comparison: baseline no-action, rule-based, nominal optimization, and stress-safe schedule. UI must show absolute values and deltas, including worsened metrics; objective choice may improve cost while raising peak. Persist failed/infeasible runs with explanation. A report exports parameters, provenance, and limitations so results are reproducible.
