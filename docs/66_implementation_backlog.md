# Small implementation tickets

Priority P0 = needed for research MVP; P1 = needed for complete demo; P2 = later. Paths refer to planned [59](59_repository_structure.md). Each ticket's acceptance is a testable outcome; no ticket authorizes live control.

| ID / title | Objective and description | Depends; likely files | Acceptance / tests | Research; priority |
|---|---|---|---|---|
| T01 Unit types | Define kW/kWh/Δ conversion and explicit unit parsing | 46; `core/units.py` | Round-trip and invalid-unit tests | H; P0 |
| T02 Time intervals | UTC half-open interval and site timezone parser | T01; `core/time.py` | 15/30/60 min, overlap, DST fixture tests | H; P0 |
| T03 Asset schemas | Typed battery/PV/grid/EV/pump/HVAC constraints | T01–02; `core/assets.py` | Reject negative rating, bad SOC/window | H; P0 |
| T04 Balance calculator | Compute physical flows and residual | T03; `core/flows.py` | Hand energy-balance cases | H; P0 |
| T05 Battery transition | Implement SOC equation, efficiency and rate checks | T03–04; `simulation/battery.py` | Min/max/efficiency tests incl. [61](61_numerical_validation.md) | H; P0 |
| T06 Service states | Track EV due energy, pump service and HVAC limits | T03; `simulation/loads.py` | Departure/window/critical tests | H; P0 |
| T07 Simulation replay | Apply a schedule and fail on infeasibility | T04–06; `simulation/engine.py` | Every-step residual and service tests | H; P0 |
| T08 Solar/weather truth | Seeded zero-at-night bounded PV and weather archetypes | T02, T07; `simulation/generator.py` | Deterministic seed, rating/night tests | H; P0 |
| T09 Demand/EV truth | Seeded calendar, critical/fixed, EV sessions | T08; `simulation/generator.py` | Repeatability and feasible obligations | H; P0 |
| T10 Baseline schedules | Create valid no-action and simple rule | T07–09; `simulation/baselines.py` | Same truth/SOC; all service met | H; P0 |
| T11 Observation operator | Aggregate, mask, noise, bias, timestamps independently | T08–10; `simulation/observer.py` | Truth unchanged; energy-preserving aggregation | H; P0 |
| T12 Dataset manifest | Hash config/version/seed and separate truth/observation | T08–11; `data/manifest.py` | Re-run checksum equality | H; P0 |
| T13 CSV normalizer | Parse interval units/sign/timezone into canonical series | T01–02; `data/ingest.py` | Valid/invalid CSV fixtures | M; P0 |
| T14 Quality metrics | Coverage/gaps/duplicates/range/cross-signal checks | T11–13; `data/quality.py` | Injected faults produce expected flags | H; P0 |
| T15 Claim readiness | Map metrics+metadata to claim states and data requests | T03, T14; `data/readiness.py` | Battery/PV/peak/tariff verdict fixtures | H; P0 |
| T16 Forecast baseline | Persistence/moving average with issue-time contract | T10–15; `forecasting/baseline.py` | No future leakage; error tests | M; P0 |
| T17 Rolling backtest | Time-split MAE/RMSE/interval status | T16; `forecasting/backtest.py` | Cutoff/holdout fixture | H; P0 |
| T18 Shared constraints and joint envelope | Solver smoke test, model common physical/service constraints once, maximize sustained up/down q with recovery | T07, T10, T15; `optimization/constraints.py`, `flexibility/envelope.py` | LP/MILP hand cases and multi-asset no-double-count tests | H; P0 |
| T19 Data ablation | Configured resolution/history/missingness grid | T11, T15, T18; `experiments/ablations.py` | Paired truth constant and metrics | H; P0 |
| T20 Stress scenarios | Generate PV/load/SOC/EV parameter stresses | T11, T17–19; `uncertainty/scenarios.py` | Seed/provenance and bounds tests | H; P0 |
| T21 Reliability replay | Commit q and score delivery/service on truth scenarios | T18, T20; `uncertainty/calibration.py` | N/success/unknown logic tests | H; P0 |
| T22 Measurement ranking | One-at-time restoration, impact/burden Pareto table | T19–21; `experiments/measurement_value.py` | Truth-free real-site label; paired results | H; P1 |
| T23 Cost objective fixture | Add tariff cost and peak epigraph to shared constraints | T07, T18; `optimization/objectives.py` | Manual 2-interval optimal case | H; P0 |
| T24 Battery/grid objective integration | Verify phase-7 direction binaries, SOC and terminal reserve under cost/peak objectives | T23; `optimization/objectives.py` | No simultaneity, min/max, terminal tests | H; P0 |
| T25 Load objective integration | Verify EV/pump/HVAC service constraints under cost/peak objectives | T24; `optimization/objectives.py` | Service/comfort/window/infeasible tests | H; P0 |
| T26 Solver adapter | HiGHS status/gap/time limit and structured failures | T23–25; `optimization/solve.py` | Optimal, timeout, infeasible fixtures | H; P0 |
| T27 Independent checker | Recompute objective/physics/service from schedule | T26; `optimization/validate.py` | Reject deliberately corrupted schedule | H; P0 |
| T28 ML comparator | Linear and tree model with rolling decision replay | T17, T26–27; `forecasting/tree.py`, `experiments/forecast_value.py` | No leakage; report RMSE and regret | H; P1 |
| T29 Scenario schema | Immutable typed overrides and paired comparator | T12, T27; `scenarios/schema.py`, `runner.py` | Same truth/baseline and hash tests | M; P1 |
| T30 Experiment runner | Expand config grid; persist failures and artifacts | T19–29; `experiments/runner.py` | Repeat experiment equivalent metrics | H; P0 |
| T31 Recommendation facts | Derive action, delta, constraints from validated run | T27, T29; `reports/recommendation.py` | Every number resolves to schedule | M; P1 |
| T32 Typed API | Site/upload/readiness/assessment/run/report endpoints | T15, T27, T30–31; `api/` | Contract/status/error tests; no actuation | L; P1 |
| T33 Readiness UI | Site/data setup and claim-specific verdict | T32; `frontend/src/pages/` | Units, provenance, limited/invalid states | M; P1 |
| T34 Comparison UI | Envelope, baseline, uncertainty, scenario plots | T32–33; `frontend/src/charts/` | Labels, bands, failure cases, synchronized axes | M; P1 |
| T35 Traceable report | Markdown/JSON schema and manifest links | T30–34; `reports/render.py` | Metric-to-run-to-data trace test | H; P1 |
| T36 Demo regression | Fixed seed 7 min run and document claims | T01–35; `scripts/demo`, `tests/e2e/` | Reproducible demo incl. missing-data degradation | H; P1 |

Ticket completion requires a small review note: tested command/result, remaining risk, and changed contract if any. Avoid combining unrelated tickets into a “build backend” task.
