# System architecture (provisional implementation design)

```
CSV/simulator → ingestion+provenance → quality/readiness → canonical time series
                                             ↓
                                forecasts + uncertainty scenarios
                                             ↓
                        feasibility envelope + baseline + optimizer
                                             ↓
                           independent metrics/validation
                                             ↓
                         structured explanations + report
                                             ↓
                              FastAPI → React UI
```

Keep a pure Python domain package for units, physical models, simulation, feasibility, optimization, forecasts, and metrics. Service functions orchestrate runs; FastAPI routes validate requests and return typed results, never contain energy logic. Persist immutable run config/results and provenance in PostgreSQL for multi-user future; SQLite is adequate for a local prototype if migrations remain portable. Large interval files may be parquet/CSV artifacts referenced by metadata rather than row-per-sample in the first build. Background job execution for long experiments is a later need; MVP can use a simple job abstraction and bounded synchronous runs.

Frontend: React/TypeScript/Vite with accessible components and restrained Tailwind styles. Charts need synchronized time axes, units, uncertainty bands, and baseline traces; choose a React plotting library after prototype. Python: NumPy/Pandas for series, scikit-learn for baselines/ML, Pyomo+HiGHS provisional for MILP, pytest for domain tests. Docker can package reproducible runs after the scientific core is stable. These are proposed choices; versions and solver distribution must be checked during implementation. [Pyomo](https://pyomo.readthedocs.io/en/latest/api/pyomo.contrib.solver.solvers.highs.Highs.html), [OR-Tools alternative](https://developers.google.com/optimization/math_opt).

Boundaries: `Dataset → QualityReport → NormalizedSeries`; `ForecastInput → ForecastResult`; `ScenarioConfig + Series → Assessment/OptimizationRun`; `Run → ValidatedMetrics → Recommendation/Report`. Every boundary includes timezone, interval length, units, provenance, and run ID. No frontend calculation of energy metrics. No operational dispatch endpoint. Authentication can be local single-user in research prototype; real data later requires explicit consent, access controls, retention, and security review.

Tradeoffs: MILP improves discrete pump and direction modeling but adds solve time; use a tiny horizon and record gap. PostgreSQL supports relational integrity but adds setup burden, so local SQLite is acceptable initially. Detailed thermal modeling risks false precision; use conservative HVAC windows until calibrated. Modular architecture is justified by experiments and testability, not by microservices.
