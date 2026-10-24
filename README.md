# Energy flexibility readiness lab (working label: FlexGrid)

The project name is undecided. This is an **advisory, simulation-first research prototype** for studying how much flexibility a campus or similar small energy site can reliably provide when its data are incomplete. It does not control equipment or claim measured grid, cost, or carbon benefits.

## Current status

The **local synthetic research app is runnable**. It includes the canonical 15-minute simulator, seeded truth and observation generation, CSV normalization and claim-specific readiness, B0/B1 baselines, simple and tree forecasts, a joint Pyomo/HiGHS sustained-response envelope, a validated cost/peak/solar-use MILP, paired stress and missing-data studies, a paired forecast-decision study with realized peak regret, a JSON experiment runner, a local SQLite-backed FastAPI service, a React interface, and a traceable Markdown/JSON report. The root page is a concise introduction with a four-step interactive product journey; `/#workspace` opens the research workspace in the same React app.

The app is advisory. It does not perform physical control. The flexibility view is explicitly a perfect-information synthetic oracle; statistical reliability remains unknown without calibrated held-out evidence. Observed CSV data can be checked for readiness and forecasted, but an observed-only dataset is not passed to the hidden-truth optimizer. The B0/B1 heuristics can report infeasibility under ramp or grid constraints rather than search for an alternative. The FlexGrid workspace includes site, EV, pump, and HVAC setup, a signal inventory, validated results, B0/B1/optimization scenario comparison on the same changed site and truth, and a traceable report. A separate stress-aware candidate selector tests fixed schedules against declared training stresses and then a distinct evaluation stress set; it is not a globally optimal robust MILP or a deployable reliability promise. The forecast-decision study compares previous-day and tree forecasts at the same issue time, scores a common synthetic future, and reports unavailable methods honestly; the tree needs seven days of prior 15-minute observations. Checked-in synthetic protocols cover missingness, one-signal restoration, and observation stress sweeps. A separate public-data benchmark reproduces observed building-load forecasting and injected sensor-stress sweeps on [I-BLEND IIIT Delhi campus meter data](https://springernature.figshare.com/articles/dataset/Energy_dataset_of_IIITD/6007637); this is not site-flexibility field validation. The executable [uncertainty matrix](docs/54_uncertainty_experiment_matrix.md) combines declared 1/2/4-hour up/down physical stresses, paired synthetic observation runs, and the public observed-load benchmark while retaining infeasible and unevaluable outcomes. A model-sensitivity view ranks response vulnerabilities under explicit PV/load/SOC/EV bounds while leaving measurement burden and field priority unknown. Long-running jobs currently execute synchronously in the local service. Real-site pilot access control, calibrated probability claims, thermal-comfort and tariff outcomes, and independent operator validation remain future work.

## Start the local app

Use Python 3.11+ and Node.js 20+ with pnpm. From the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e backend
PYTHONPATH=backend/src .venv/bin/uvicorn energy_lab.api.app:app --host 127.0.0.1 --port 8765
```

In another terminal:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://127.0.0.1:5173/` for the introduction, then select **Open workspace**. The API binds to loopback only; Vite proxies `/v1` to port 8765. After `pnpm build`, FastAPI also serves the built client at `http://127.0.0.1:8765/`, so the Vite server is optional for normal use. Generated local metadata and experiment artifacts are under `.local/` and ignored by Git.

## Run the tests

With the virtual environment installed:

```bash
PYTHONPATH=backend/src .venv/bin/python -m unittest discover -s backend/tests -v
```

Build the frontend and run the reproducible synthetic demonstration:

```bash
cd frontend && pnpm build && cd ..
PYTHONPATH=backend/src .venv/bin/python scripts/demo.py
PYTHONPATH=backend/src .venv/bin/python scripts/run_experiment.py configs/experiments/paired_missingness.json
PYTHONPATH=backend/src .venv/bin/python scripts/run_full_uncertainty_matrix.py --output-dir .local/uncertainty_matrix
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

The exact inputs and checks for a real-site study are in [the pilot validation gate](docs/pilot_validation.md). No private pilot data should be committed to this public repository.
