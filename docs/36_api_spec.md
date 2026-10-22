# API contracts (draft, v1)

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) fixes sign/unit fields and [49_data_readiness_implementation.md](49_data_readiness_implementation.md) fixes readiness verdict names.

All payloads have `schema_version`, explicit unit fields, ISO-8601 timestamps, site timezone, and typed errors (`code`, `message`, `field`, `run_id`). Long runs return `202` and a job ID; retrieval returns `pending|running|succeeded|infeasible|failed`. No live control endpoint.

| Method/path | Request essentials | Success response essentials |
|---|---|---|
| `POST /v1/sites` | `{name,timezone,grid_import_limit_kw,grid_export_limit_kw}` | `{site_id,...}` |
| `POST /v1/sites/{id}/datasets` | multipart file + `{quantity,unit,interval_minutes,timezone,source,synthetic}` | `{dataset_id,checksum,import_status}` |
| `POST /v1/datasets/{id}/validate` | `{claim_types:[...]}` | `{quality_report_id,issues:[{code,severity,interval}],readiness:{claim:level}}` |
| `GET /v1/quality-reports/{id}` | — | report, missing data recommendations, provenance |
| `POST /v1/sites/{id}/forecasts` | `{target,horizon_start,horizon_end,interval_minutes,model_id,dataset_ids}` | `{forecast_id,job_id}` |
| `POST /v1/sites/{id}/flexibility-assessments` | `{scenario_id,baseline_id,direction,windows:[{start,end}],method,uncertainty_model_id?}` | `{assessment_id,job_id}` |
| `POST /v1/sites/{id}/optimization-runs` | `{scenario_id,forecast_ids,objective_profile,weights?,solver_limit_s}` | `{run_id,job_id}` |
| `POST /v1/sites/{id}/scenarios` | typed `ScenarioConfig` with asset overrides, tariff ID, dataset IDs, seed | `{scenario_id}` |
| `POST /v1/experiments` | `{protocol_id,scenario_ids,seed_set}` | `{experiment_id,job_id}` |
| `GET /v1/runs/{id}` | — | status, config hash, interval schedule with `kw/kwh`, metrics, residuals, warnings |
| `GET /v1/recommendations?run_id=` | — | structured action, baseline delta, assumptions, reliability provenance |
| `GET /v1/reports/{run_id}` | `format=json|markdown` | versioned report or download link |

`ScenarioConfig` has typed nested `Grid`, `PV`, `Battery`, `EVSession[]`, `Pump`, `HVAC`, `TariffRef`, `DataRef`, and `UncertaintyRef`; each validator checks units and time windows. `AssessmentResult` stores `{window,direction,theoretical_kw,technical_kw,operational_kw,reliable_kw|null,duration_h,energy_kwh,method,sample_count|null}`. `MetricValue` is `{value,unit,baseline_value?,delta?,status,source}`. Invalid units or infeasible input use `422`; solver infeasibility is a completed analytical status, not a server crash. Access to real datasets requires authorization once pilot data exist.
