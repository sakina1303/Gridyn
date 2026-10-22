# Baseline and comparator hierarchy

All strategies use identical hidden truth, site/asset constraints, initial SOC, tariff, evaluation period and terminal/recovery treatment. The difference is **information and decision policy**, not the physical world.

| Label | Information available when deciding | Policy and role |
|---|---|---|
| B0 valid no-new-action | Fixed schedules and known asset obligations; no future truth | EV/pump/HVAC service at predeclared valid times, battery idle; causal comparator for changed schedule |
| B1 transparent rule | Current observations and declared schedule/weather class | Fixed solar-first/peak-avoid rules, no future truth; practical competitor |
| B2 perfect information | Full future hidden truth | Same optimization constraints/objective; oracle upper bound, never deployable claim |
| B3 forecast-based | Observed data and forecasts issued at decision time | Nominal MILP; tests forecast value |
| B4 uncertainty-aware | Same observations plus calibrated intervals or declared stress set | Commit-safe/stress-tested MILP; proposed method |
| B5 conservative robust (optional) | Same observations and worst-case uncertainty set | Sensitivity comparator; may be overly conservative |

Evaluate realized outcomes after replay, not only planned objective. Baselines B0/B1 must meet all services; B2 must not be described as “savings available to operator.” If B4 uses more data than B3, stratify by information set before claiming method gain. No strategy may see hidden truth except B2. Each run records its information set and decision time.
