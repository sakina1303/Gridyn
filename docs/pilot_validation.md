# Real-site validation gate

**Status:** pending. No consented facility dataset or operator review is attached to this repository. Current numerical outcomes are synthetic research results.

A separate [public I-BLEND building-meter benchmark](54_uncertainty_experiment_matrix.md#current-execution-boundary) tests observed-load forecasting on openly released CC0 campus measurements from IIIT Delhi. It is an external benchmark, not an operator-approved FlexGrid pilot: it lacks verified site import, PV, flexible-asset service and control logs, a tariff and operator sign-off. Its observed load values must not be relabeled as a delivered flexibility response.

The [uncertainty matrix](54_uncertainty_experiment_matrix.md#current-execution-boundary) now has an executable synthetic physical stress audit for 1/2/4-hour up/down responses and a paired observation audit. These exercise the model's rejection and abstention paths. They do not replace the consented site, asset, and operator evidence listed below.

## Inputs needed from a pilot site

1. A named facility contact, permission to use the data for this research, and agreed retention/access rules. Do not place private pilot data in the public Git repository.
2. Site timezone, grid import/export limits, PV capacity, battery capacity/rates/efficiency and allowed SOC range, and the operator-approved EV, pump and HVAC service constraints.
3. Timestamped site import/export and PV readings, preferably 15-minute intervals, with units, meter sign convention, coverage period, gaps and source provenance. Battery SOC/AC power and flexible-asset logs are needed for corresponding firm asset claims.
4. The applicable tariff order, category, effective dates, demand-charge and export rules **only** if a cost claim is to be evaluated. No tariff value is assumed by the model.
5. Operator notes on critical loads, prohibited actions, comfort limits, asset availability and what constitutes an acceptable recommendation.

The ingestion and claim-specific readiness workflow can inspect observed CSV data now. It does not use unobserved future truth to optimize an observed-only dataset.

## Validation sequence

1. Record consent and keep the raw data outside this public repository. Normalize units and UTC intervals; retain raw source files and quality flags.
2. Audit coverage, missingness, duplicates, physical ranges, meter balance and asset metadata. Publish readiness per claim, with abstention where needed.
3. Freeze training, calibration and later test periods chronologically. Record the exact code revision, data hashes, issue times, seeds, solver and tariff version.
4. Run forecasts and advisory schedules in shadow mode. Replay against held-out measurements and check power balance, SOC, critical service, EV/pump service and comfort constraints.
5. Compare B0, B1, optimization and stress-aware candidate selection under the same site obligations. Record infeasible, failed and abstained cases rather than dropping them.
6. Review constraints, outputs and failure cases with the facility operator. Log corrections and rerun the frozen evaluation before making any field-facing claim.

## Release boundary

Until those steps pass, statistical field reliability, measured savings, carbon reduction, grid benefit and operator acceptance remain **Unknown**. The software remains advisory and has no equipment-control endpoint. A real pilot additionally needs access control and a security/privacy review before private data are served beyond a single-user local environment.
