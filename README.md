# Energy flexibility readiness lab (working label: FlexGrid)

The project name is undecided. This is an **advisory, simulation-first research prototype** for studying how much flexibility a campus or similar small energy site can reliably provide when its data are incomplete. It does not control equipment or claim measured grid, cost, or carbon benefits.

## Current status

Phases 0–6 are implemented: canonical units and UTC intervals, typed site/asset constraints, AC-bus power balance, battery SOC transitions, EV and pump service tracking, conservative HVAC bounds, and a deterministic 15-minute simulator that replays a supplied schedule. Seeded synthetic truth generation and an independent observation layer can produce missing, noisy, aggregated or time-shifted data for research tests. CSV ingestion, quality checks, and claim-specific readiness are present. Two causal comparator schedules (B0 fixed earliest service and B1 calendar solar-hour preference) are validated by simulator replay. Issue-time-bounded previous-day/week, hour/day mean, and calendar ridge forecasts have rolling backtests.

The joint flexibility envelope, MILP optimization, uncertainty calibration, experiment runner, API, UI, and real-data integrations are not implemented. Phase 7 requires a MILP solver; no solver is installed in the current Python environment. The baseline heuristics may report infeasibility for a site with ramp or grid constraints rather than search for a feasible alternative. Forecast error results from synthetic truth are research fixtures, not field performance claims.

## Run the tests

Use Python 3.11 or newer. The implemented core uses only the standard library.

```bash
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests -v
```

Run a small reproducible synthetic-data demonstration:

```bash
PYTHONPATH=backend/src python3 scripts/generate_synthetic_demo.py
```

## Physical convention

All gross flows are nonnegative average kW. Grid import is positive; grid export is a separate nonnegative flow. For every interval:

```text
PV available − PV curtailed + grid import + battery discharge
  = critical load + fixed load + flexible load + battery charge + grid export
```

Battery energy is kWh at interval start; AC-side charge/discharge efficiency and SOC bounds are enforced. Interval energy is `average kW × interval hours`. The simulator uses 15-minute truth intervals; the domain time layer also supports 30 and 60 minutes for later observation studies. See [the canonical model](docs/46_canonical_model.md) and [simulator contract](docs/47_simulator_spec.md).

## Example

```python
from datetime import datetime, timezone
from energy_lab.core.assets import GridConfig, PVConfig, SiteConfig
from energy_lab.core.time import make_intervals
from energy_lab.simulation.engine import CandidateScheduleStep, TruthDisturbance, simulate

intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 4, 15)
site = SiteConfig("campus", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0))
truth = tuple(TruthDisturbance(t, 0, 5, 3) for t in intervals)
schedule = tuple(CandidateScheduleStep(t) for t in intervals)
trajectory = simulate(site, truth, seed=1, schedule=schedule)
assert trajectory.grid_import_kwh == 8.0
```

Set `PYTHONPATH=backend/src` when running this example from the repository root.

## Data and comparator contracts

`energy_lab.data.ingest.ingest_csv_text` accepts `start,end,quantity,value,unit` rows. Timestamps with an offset are normalized to UTC. Naive timestamps use the supplied IANA site timezone; ambiguous local times need `start_fold` and `end_fold`. Interval energy readings are converted once to average kW. The quality report retains suspect records and flags gaps, duplicates, invalid gross values, possible outliers, and sustained cross-signal imbalance. Readiness is decided per claim and synthetic data cannot support a measured-peak claim.

`energy_lab.simulation.baselines.build_baseline` produces B0 or B1 without access to future truth. `evaluate_baseline` then replays the schedule against a chosen truth trace. `energy_lab.forecasting.baseline.issue_forecast` only trains on observations whose intervals end by the issue time. `rolling_backtest` records per-fold and pooled MAE/RMSE in kW.

## Research path

The approved direction and scope are in [the architecture decision](docs/44_final_architecture_decision.md). [The implementation plan](docs/58_implementation_plan.md) and [small tickets](docs/66_implementation_backlog.md) order the work. The central research question is whether a site can produce a useful, calibrated flexibility response envelope from limited observations, and which additional measurement most improves that decision. Synthetic results must remain labeled as synthetic; a later pilot requires consented data and independent validation.
