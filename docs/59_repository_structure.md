# Planned repository structure

One modular Python backend plus one React client; no microservices. `energy_lab` is a neutral package identifier, not the product name.

```text
backend/
  pyproject.toml
  src/energy_lab/
    core/                 # canonical units, time, assets, flows
    simulation/           # deterministic physics, generator, observer, baselines
    data/                 # CSV normalization, quality, readiness, provenance
    forecasting/          # baselines, ML comparators, time-split backtests
    flexibility/          # joint response envelope
    uncertainty/          # scenarios, calibration, deliverability tests
    optimization/         # Pyomo model, solver adapter, independent validator
    scenarios/            # immutable overrides and paired comparisons
    experiments/          # config-driven runner and metrics
    reports/              # traceable report schema/rendering
    api/                  # FastAPI routes and typed schemas
    db/                   # local metadata persistence/migrations
  tests/                  # unit, property, numerical, API, reproducibility
frontend/
  src/{api,components,pages,charts,types}/
configs/
  archetypes/             # synthetic assumptions, versioned
  experiments/            # protocol specs and seed sets
datasets/
  synthetic/              # generated, checksum-manifested; large data ignored by VCS
  examples/               # tiny non-sensitive fixtures
reports/                  # generated research artifacts, manifest-backed
docs/                     # research, design and implementation decisions
scripts/                  # reproducible entry points, not business logic
```

Rules: no physics inside API or React; no experiment-specific branches in simulator; no raw facility data committed; no duplicated unit conversions. SQLite is acceptable for local metadata, with a schema that can migrate to PostgreSQL if real multi-user data justify it. Use files for large time series plus checksums, metadata tables for IDs/provenance. Docker is packaging after core validation. Generated outputs live outside source and are reproducible from configs.
