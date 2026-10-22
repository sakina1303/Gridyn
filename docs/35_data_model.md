# Data model (logical schema)

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) fixes temporal and unit conventions; [57_report_schema.md](57_report_schema.md) defines traceable result metadata. `ResponseEnvelope` is a typed assessment result, not a separate database entity.

Identifiers are UUIDs; timestamps UTC with site IANA timezone, interval start/end, and unit metadata. Every analytical record has `provenance` (`observed`, `operator`, `inferred`, `synthetic`), version, creator, and creation time. Avoid storing arbitrary JSON for core constraints.

| Entity | Key fields and relationships |
|---|---|
| User | `id`, display name, role; optional in local mode, no elaborate RBAC yet |
| Site | `id`, name, timezone, location granularity, grid import/export limits, owner/user |
| Asset | `id`, `site_id`, type, rated kW/kWh, efficiency, criticality, operating constraint version; subtype fields for battery/EV/HVAC/pump |
| Meter | `id`, `site_id`, optional `asset_id`, quantity, unit, interval convention, sign convention |
| Dataset | `id`, source/license, checksum, synthetic flag, period, resolution, schema version, file location |
| TimeSeries | `id`, dataset/meter/asset, quantity, interval start/end, value/unit, quality flag; partition or artifact backed for large data |
| Tariff | `id`, jurisdiction, category, effective dates, source URL/version, interval prices, demand/export terms |
| Weather | dataset-linked interval variables, units, location and forecast issue time where applicable |
| DataQualityReport | `id`, dataset/site, checks, missingness, gaps, provenance, claim-specific readiness levels |
| Forecast | `id`, site, target, model/version, train cutoff, horizon, values/intervals, evaluation metrics, dataset IDs |
| UncertaintyModel | `id`, sources, method, parameters/scenario references, calibration period, limitations |
| Scenario | `id`, site, parent, immutable config, truth dataset, observed dataset, tariff, seed |
| FlexibilityAssessment | `id`, scenario, baseline run, direction/window, theoretical/technical/operational/reliable envelopes, method |
| OptimizationRun | `id`, scenario, forecast, objective, solver/version/status/gap, schedule artifact, validation residuals |
| Recommendation | `id`, run, asset, action, evidence fields, confidence status, explanation template version |
| Experiment | `id`, protocol version, hypotheses, scenario/run IDs, metrics, seed, code/data checksums |

Foreign keys and immutable versions prevent a changed tariff or asset rating from silently rewriting past results. Separate observed from synthetic data at dataset level and in UI. Retain consent and deletion metadata for real site data. Define migration and retention policy before a real pilot.
