# Optimization formulation

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) and [53_optimizer_implementation.md](53_optimizer_implementation.md). The first benchmark uses a 24-hour schedule with explicit recovery/terminal handling; 48-hour horizons are later sensitivity tests.

## Decision and selection

Select a small **mixed-integer linear program (MILP)** on a 24–48 hour horizon, timestep `Δt` hours. Linear dispatch handles PV, battery, import/export, and divisible EV energy; binary variables prevent simultaneous battery charge/discharge and grid import/export, and represent pump on/off. Start with a continuous LP variant for debugging. Pyomo plus an available HiGHS solver is the provisional implementation choice because it expresses algebraic constraints clearly and supports LP/MILP; verify installation and solve performance before lock. [Pyomo solver docs](https://pyomo.readthedocs.io/en/latest/api/pyomo.contrib.solver.solvers.highs.Highs.html). OR-Tools MathOpt also supports LP/MIP and is a reasonable alternative; CVXPY is useful for convex LP/QP but mixed-integer solver availability adds a deployment choice. [OR-Tools](https://developers.google.com/optimization/math_opt).

## Variables and constraints

For each `t`: grid import `i_t`, export `e_t`, PV curtailment `u_t`, battery charge `c_t`, discharge `d_t`, SOC `E_t`, EV power `v_jt`, pump on `z_pt∈{0,1}`, HVAC power or shift `h_t`, peak epigraph `K`, and optional noncritical service slack `s_j≥0`. Battery and grid direction binaries enforce `c_t≤Cmax y_t`, `d_t≤Dmax(1−y_t)` and analogous import/export constraints. Bound PV, grid, and asset rates. Impose energy balance exactly as in [22](22_flexibility_model.md), SOC dynamics/terminal reserve, EV energy by departure, pump service/operating window, comfort constraint if calibrated, critical demand fixed, `K≥i_t`, and optional ramp limits. Reject incompatible windows or bounds before solve. Constraint tolerances and max optimality gap must be recorded.

## Objective

Primary demo objective: `min Σ_t (π_import,t i_t−π_export,t e_t)Δt + λ_peak K + λ_curt Σ_t u_tΔt + λ_batt Σ_t(c_t+d_t)Δt + Σ_j λ_service,j s_j`. Currency and penalty units must be consistent and shown. Use **one named objective profile** at a time: `cost`, `peak`, or `solar-use`; do not imply a universal optimum. Critical load and physical limits are hard constraints. EV/pump service is hard in the base model; slack is allowed only in an explicit diagnostic run to quantify why infeasible, never hidden in a recommended schedule. Battery throughput cost is a simple proxy, not a validated degradation model. Export credit may be zero depending on tariff scenario.

For reliability, first solve nominal. Then solve against a small fixed stress set with shared first-stage schedule and scenario-specific energy balance; only adopt this if runtime and feasibility remain acceptable. Otherwise evaluate nominal schedules under scenarios and display failure. Avoid claiming probabilistic optimality from hand-picked stresses.

Feasibility checks: initial SOC within range; each load's maximum available energy ≥ required service; fixed load/grid/PV/battery bounds capable of balance; tariff coefficients do not create unrestricted arbitrage; terminal battery target attainable. Post-solve recompute all residuals in independent metric code. If infeasible/time limit/no incumbent, return status and no recommendation.
