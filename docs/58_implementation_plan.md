# Executable, dependency-ordered implementation plan

Planning only; no application code has been written. Complexity is relative for a student team: S (small), M (medium), L (large). Research significance H/M/L describes contribution to the central hypothesis, not engineering importance. Paths are **planned**, not existing files. Every phase records a manifest and passes tests before the next dependent phase.

| Phase | Objective; inputs → outputs | Dependencies | Likely files | Tests / definition of done | Complexity; research |
|---|---|---|---|---|---|
| 0 Review | Resolve numbering, frozen contracts and evidence gates → reviewed spec | 15–57 | `docs/45–67`, `configs/decision_log.yaml` | All links/terms consistent; unresolved field claims explicit | M; H |
| 1 Canonical core | Units, half-open UTC intervals, typed assets/flow states → validated domain types | 46 | `backend/src/energy_lab/core/{units,time,assets,flows}.py` | Conversion/sign/SOC hand cases; no ambiguous units | M; H |
| 2 Physical simulator | Pure transition, balance and service checks → truth trace for supplied disturbances/schedule | 1, 47 | `simulation/{engine,battery,loads,grid}.py` | Power balance, SOC, windows, no hidden shedding | L; H |
| 3 Generator/observer | Seeded weather/load/assets and independent corruption → truth/observed datasets | 2, 48 | `simulation/{generator,observer}.py`, `configs/archetypes/` | Same hash on rerun; observed never leaks truth | L; H |
| 4 Readiness | Parse/normalize CSV and claim-specific quality gates → report/status | 1, 3, 49 | `data/{ingest,quality,readiness}.py` | Missing/duplicate/unit/timezone fixtures, severity mapping | M; H |
| 5 Baselines | Valid no-action and transparent rule → paired benchmark traces | 2–4, 52 | `simulation/baselines.py` | Identical truth/initial SOC; all service met | M; H |
| 6 Simple forecasts | Persistence, moving average, linear baseline + rolling backtest → issued forecast object | 3–5, 55 | `forecasting/{baseline,backtest}.py` | No future leakage; error units and cutoff recorded | M; M |
| 7 Constraint kernel + full-info envelope | Solver smoke test; one shared joint asset/energy formulation, then up/down max over window+recovery → oracle envelope | 2, 5, 50 | `optimization/constraints.py`, `flexibility/envelope.py` | LP/MILP feasibility, single/multi-asset manual cases, no double count | L; H |
| 8 Incomplete-data ablations | Mask/aggregate observation, infer bounds/abstain → error-vs-data curves | 3–7, 25 | `experiments/ablations.py`, `configs/experiments/data_*.yaml` | Paired truth fixed; overstatement and abstention computed | L; H |
| 9 Uncertainty | Stress/residual scenarios and held-out calibration → qualified reliability | 6–8, 23, 54 | `uncertainty/{scenarios,calibration}.py` | Scenario provenance; no uncalibrated probability | L; H |
| 10 MILP cost/peak optimizer | Reuse phase-7 constraint kernel; add named objectives, 24 h schedule and independent checker → validated run/status | 2, 5, 7–9, 53 | `optimization/{objectives,solve,validate}.py` | All [61](61_numerical_validation.md) cases; zero hard residual | L; H |
| 11 Forecast decision study | Tree comparator and replay through identical optimizer → error/regret table | 6, 10, 55 | `forecasting/tree.py`, `experiments/forecast_value.py` | Rolling split; compare decision quality, not RMSE alone | M; H |
| 12 Scenario engine | Immutable overrides/paired comparisons → scenario result records | 3–11, 30 | `scenarios/{schema,runner}.py` | Same hidden truth and baseline for paired runs | M; M |
| 13 Experiment runner | Configuration expansion, manifests, hashes → reproducible experiment artifacts | 8–12, 56 | `experiments/{spec,runner,metrics}.py`, `configs/experiments/` | Rerun reproduces data and equivalent metrics | M; H |
| 14 API | Typed site/dataset/assessment/run/report routes → local service | 4, 10, 12–13, 36 | `api/{routes,schemas}.py`, `db/` | Schema/error/status contract tests; no control endpoint | M; L |
| 15 Focused frontend | Setup, readiness, assessment, scenario, report UI → usable demo | 14, 37 | `frontend/src/{pages,components,api}/` | Labels, units, synthetic badge, uncertainty/failure states | L; M |
| 16 Research report | Traceable Markdown/JSON report and figures → operator/research export | 13–15, 57 | `reports/{schema,render}.py` | Every metric resolves to run/data; failures visible | M; H |
| 17 Validation/demo | End-to-end registered experiments, numerical review, 7 min story → release candidate | 1–16, 38, 42 | `tests/`, `scripts/demo`, `reports/demo/` | Reproducible demo; no unsupported claims; review signoff | L; H |

Critical sequence is 1→2→3→4/5→7→8→9→10→13→14→15/16→17. Forecast baselines can develop after generator and alongside readiness/envelope; UI design can be sketched independently but should not consume implementation capacity before validated numerical outputs. Stage 0 evidence gates (operator interviews, prior-art depth, real dataset/tariff audit) are required before *field* claims, but not for simulation-first implementation if explicitly labeled.

Operational limits: keep first fixture to 24 h/96 intervals, one site, one battery, aggregate EV, one pump and one conservative HVAC load. Defer sophistication if it threatens invariant tests. Each stage ends with an auditable artifact and a single acceptance decision; later phases cannot repair an unvalidated physical core by visual presentation.
