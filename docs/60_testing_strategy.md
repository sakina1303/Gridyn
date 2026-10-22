# Testing strategy and invariant ownership

| Layer | Test type and fixtures | Required assertions |
|---|---|---|
| Core units/time | Small unit/property tests over 15/30/60 min, local/UTC conversions, DST edge | `ΣkWΔ=kWh`, half-open nonoverlap, conversion reversibility within tolerance |
| Physical model | Hand cases plus seeded property tests | Balance residual, nonnegative gross flows, PV used≤available, critical served, SOC/ratings/windows/ramp/terminal bounds |
| Generator/observer | Same-seed replay and corruption masks | Deterministic checksum, truth untouched by observation corruption, energy-preserving aggregation |
| Data quality | Fixtures for gaps, duplicates, impossible values, unknown units, timestamp shifts | Correct severity/claim gate; raw records retained |
| Envelope | Single/multiple asset analytical cases | Sustained response feasible across whole window and recovery; no sum-of-nameplates error |
| Optimizer | LP/MILP small cases, infeasible and timeout cases | Status/gap truthful; independent validator rejects any hard violation |
| Forecast/uncertainty | Chronological split and calibration fixture | No future features/leakage, coverage measured on holdout, unknown when uncalibrated |
| Experiment | Config+seed rerun | Identical dataset hashes and equivalent numeric metrics; all failures retained |
| API | Schema/validation/status/error tests | Units explicit, invalid input 422, no actuation route |
| Frontend | Focused component/e2e tests | Correct synthetic label, units, unknown/infeasible display, report trace link |

Use Hypothesis or equivalent property tests where invariants span many configurations, but keep explicit analytical regressions in [61](61_numerical_validation.md). Relative/absolute numerical tolerance is defined centrally (e.g. `max(1e−6 kW, 1e−7×site_rating_kW)` for balance in hand fixtures; solver-specific tolerance tested separately). Never loosen tolerance solely to make a failed test pass. Avoid tests that merely mirror an implementation branch; assert physics and information boundaries.
