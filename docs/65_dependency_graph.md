# Dependency graph and critical path

```mermaid
flowchart LR
  R[Research and approved decision] --> C[Canonical units and model]
  C --> S[Physical simulator]
  S --> G[Seeded truth and observations]
  G --> Q[Data quality and readiness]
  S --> B[Valid baselines]
  G --> B
  Q --> F[Forecast baselines]
  B --> E[Full-info envelope]
  Q --> A[Missing-data ablations]
  E --> A
  F --> U[Uncertainty scenarios]
  A --> U
  E --> O[MILP and validator]
  U --> O
  O --> X[Experiments and metrics]
  X --> API[Typed API]
  API --> UI[Focused UI]
  X --> REP[Traceable report]
  UI --> D[Demo and validation]
  REP --> D
```

Critical path: canonical model → simulator → deterministic truth/observation → valid baseline → joint envelope → low-data and uncertainty tests → MILP/independent validation → experiment runner → report/demo. Data readiness and forecast baselines can develop in parallel after the generator; UI component design and report schema can be designed in parallel but implementation depends on stable numerical contracts. API and report rendering can begin together after experiment/result schemas settle. Blockers: missing physical convention, non-reproducible generator, truth leakage, invalid baseline, no feasible validated optimizer, or untraceable results. Real operator interviews and real data are **field claim** gates, not simulation-core blockers.
