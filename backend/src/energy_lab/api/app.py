"""Local-only advisory API over persisted sites, datasets and validated runs."""

from __future__ import annotations

import os
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from energy_lab.advisory.decision import build_decision_brief
from energy_lab.core.time import make_intervals
from energy_lab.data.ingest import DataIngestionError, ingest_csv_text
from energy_lab.data.quality import assess_quality
from energy_lab.data.readiness import assess_readiness
from energy_lab.data.serde import (record_from_dict, record_to_dict, schedule_from_dict, schedule_to_dict,
                                   site_from_dict, site_to_dict, truth_from_dict, truth_to_dict)
from energy_lab.db.store import LocalStore
from energy_lab.experiments.runner import load_spec, run_experiment
from energy_lab.experiments.forecast_value import compare_forecast_decisions
from energy_lab.experiments.measurement_sensitivity import assess_measurement_sensitivity
from energy_lab.flexibility.envelope import assess_envelope
from energy_lab.forecasting.baseline import issue_forecast
from energy_lab.forecasting.tree import issue_tree_forecast
from energy_lab.optimization.objectives import ObjectiveConfig
from energy_lab.optimization.solve import solve_schedule
from energy_lab.reports.render import render_markdown
from energy_lab.reports.schema import make_report
from energy_lab.simulation.baselines import build_baseline
from energy_lab.simulation.engine import InfeasibleSchedule, simulate
from energy_lab.simulation.generator import GenerationConfig, generate_truth
from energy_lab.simulation.observer import ObservationConfig, observe_truth
from energy_lab.scenarios.runner import compare_scenario
from energy_lab.scenarios.schema import ScenarioConfig
from energy_lab.scenarios.stress_aware import declared_stress_sets, select_stress_aware_schedule

from .schemas import (AssessmentInput, ForecastInput, ForecastStudyInput, OptimizationInput, SiteCreate,
                      ScenarioInput, ExperimentInput, SyntheticCreate, ValidateInput)


def _new_id() -> str:
    return str(uuid.uuid4())


def _error(code: str, message: str, status: int = 422, *, field: str | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, "field": field, "run_id": None})


def create_app(db_path: Path | None = None) -> FastAPI:
    path = db_path or Path(os.environ.get("ENERGY_LAB_DB_PATH", ".local/energy_lab.sqlite3"))
    store = LocalStore(path)
    app = FastAPI(title="Energy Lab advisory API", version="0.1.0")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        first = exc.errors()[0]
        return JSONResponse(status_code=422, content={"code": "invalid_request", "message": first["msg"],
                                                     "field": ".".join(str(x) for x in first["loc"]), "run_id": None})

    def stored(kind: str, object_id: str) -> dict:
        item = store.get(kind, object_id)
        if item is None:
            raise _error("not_found", f"{kind} {object_id} not found", 404)
        return item

    def site_for(site_id: str):
        return site_from_dict(stored("site", site_id)["config"])

    def dataset_for(site_id: str, dataset_id: str) -> dict:
        data = stored("dataset", dataset_id)
        if data["site_id"] != site_id:
            raise _error("site_dataset_mismatch", "dataset does not belong to site", 404)
        return data

    @app.get("/v1/health")
    def health():
        return {"status": "ok", "schema_version": "1", "control_enabled": False}

    @app.get("/v1/public-benchmarks/iblend-academic")
    def get_public_iblend_benchmark():
        path = Path(__file__).resolve().parents[4] / "configs" / "public_benchmarks" / "iblend_academic_summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/v1/public-benchmarks/etsit-building-c")
    def get_public_etsit_benchmark():
        path = Path(__file__).resolve().parents[4] / "configs" / "public_benchmarks" / "etsit_paired_summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/v1/uncertainty-matrix")
    def get_uncertainty_matrix():
        path = Path(__file__).resolve().parents[4] / "configs" / "uncertainty_matrix_summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @app.post("/v1/sites", status_code=201)
    def create_site(body: SiteCreate):
        site_id = _new_id()
        raw = body.model_dump(mode="json", exclude={"name", "schema_version"})
        raw["site_id"] = site_id
        try:
            site = site_from_dict(raw)
        except ValueError as exc:
            raise _error("invalid_site", str(exc)) from exc
        payload = {"schema_version": "1", "site_id": site_id, "name": body.name,
                   "config": site_to_dict(site)}
        store.put("site", site_id, payload)
        return payload

    @app.get("/v1/sites")
    def list_sites():
        return {"schema_version": "1", "sites": store.list("site")}

    @app.get("/v1/sites/{site_id}")
    def get_site(site_id: str):
        return stored("site", site_id)

    @app.post("/v1/sites/{site_id}/synthetic-datasets", status_code=201)
    def create_synthetic(site_id: str, body: SyntheticCreate):
        site = site_for(site_id)
        dataset_id = _new_id()
        try:
            generated = generate_truth(GenerationConfig(dataset_id, site, body.start_utc,
                body.interval_count, body.seed, body.weather_scenario, body.load_scenario,
                body.solar_scenario, body.critical_base_kw, body.fixed_base_kw,
                body.day_activity_kw, body.evening_activity_kw, body.cooling_kw_per_c_above_28))
            observed = observe_truth(generated, ObservationConfig(dataset_id + "-observed", body.seed)).observed
        except ValueError as exc:
            raise _error("invalid_synthetic_config", str(exc)) from exc
        payload = {"schema_version": "1", "dataset_id": dataset_id, "site_id": site_id,
                   "evidence_kind": "synthetic", "synthetic": True,
                   "truth_sha256": generated.manifest.truth_sha256,
                   "observed_sha256": observed.manifest.observed_sha256,
                   "site_snapshot": site_to_dict(generated.site),
                   "start_utc": generated.disturbances[0].interval.start.isoformat(),
                   "end_utc": generated.disturbances[-1].interval.end.isoformat(),
                   "interval_minutes": 15,
                   "records": [record_to_dict(item) for item in observed.records],
                   "truth": [truth_to_dict(item) for item in generated.disturbances]}
        store.put("dataset", dataset_id, payload)
        return {key: payload[key] for key in ("schema_version", "dataset_id", "site_id", "synthetic",
                                              "truth_sha256", "observed_sha256", "start_utc", "end_utc", "interval_minutes")}

    @app.post("/v1/sites/{site_id}/datasets", status_code=201)
    async def upload_dataset(site_id: str, file: UploadFile = File(...),
                             interval_minutes: int = Form(...), source: str = Form("user_upload")):
        site = site_for(site_id)
        dataset_id = _new_id()
        try:
            contents = (await file.read()).decode("utf-8")
            imported = ingest_csv_text(contents, dataset_id=dataset_id, site_timezone=site.timezone)
        except (UnicodeError, DataIngestionError, ValueError) as exc:
            raise _error("invalid_dataset", str(exc), field="file") from exc
        if interval_minutes not in (15, 30, 60):
            raise _error("invalid_resolution", "interval_minutes must be 15, 30 or 60", field="interval_minutes")
        records = imported.records
        payload = {"schema_version": "1", "dataset_id": dataset_id, "site_id": site_id,
                   "evidence_kind": "observed", "synthetic": False, "source": source,
                   "source_sha256": imported.source_sha256,
                   "observed_sha256": imported.normalized_sha256,
                   "start_utc": min(item.interval.start for item in records).isoformat(),
                   "end_utc": max(item.interval.end for item in records).isoformat(),
                   "interval_minutes": interval_minutes,
                   "records": [record_to_dict(item) for item in records]}
        store.put("dataset", dataset_id, payload)
        return {"schema_version": "1", "dataset_id": dataset_id,
                "checksum": imported.normalized_sha256, "import_status": "normalized"}

    @app.get("/v1/datasets/{dataset_id}")
    def get_dataset(dataset_id: str):
        item = stored("dataset", dataset_id)
        return {key: value for key, value in item.items() if key not in {"truth", "records"}}

    @app.get("/v1/datasets/{dataset_id}/observations")
    def get_observations(dataset_id: str):
        item = stored("dataset", dataset_id)
        return {"schema_version": "1", "dataset_id": dataset_id, "synthetic": item["synthetic"],
                "records": item["records"]}

    @app.post("/v1/datasets/{dataset_id}/validate")
    def validate_dataset(dataset_id: str, body: ValidateInput):
        data = stored("dataset", dataset_id)
        site = site_from_dict(data.get("site_snapshot") or stored("site", data["site_id"])["config"])
        records = tuple(record_from_dict(item) for item in data["records"])
        try:
            quality = assess_quality(records,
                expected_start_utc=datetime.fromisoformat(data["start_utc"]),
                expected_end_utc=datetime.fromisoformat(data["end_utc"]),
                declared_resolution_minutes=data["interval_minutes"],
                site_timezone=site.timezone, site_rating_kw=site.grid.import_limit_kw,
                pv_capacity_kw=site.pv.ac_capacity_kw)
            readiness = assess_readiness(quality, site, evidence_kind=data["evidence_kind"],
                                         tariff_verified=body.tariff_verified)
        except ValueError as exc:
            raise _error("quality_failed", str(exc)) from exc
        report_id = _new_id()
        payload = {"schema_version": "1", "quality_report_id": report_id, "dataset_id": dataset_id,
                   "quality": jsonable_encoder(quality), "readiness": jsonable_encoder(readiness)}
        store.put("quality_report", report_id, payload)
        return {"quality_report_id": report_id, "issues": payload["quality"]["issues"],
                "readiness": {item["claim"]: item["state"] for item in payload["readiness"]["claims"]}}

    @app.get("/v1/quality-reports/{report_id}")
    def get_quality(report_id: str):
        return stored("quality_report", report_id)

    @app.post("/v1/sites/{site_id}/forecasts", status_code=201)
    def create_forecast(site_id: str, body: ForecastInput):
        data = dataset_for(site_id, body.dataset_id)
        site = site_for(site_id)
        records = tuple(record_from_dict(item) for item in data["records"])
        intervals = make_intervals(body.issue_at_utc, body.horizon_intervals, 15)
        try:
            if body.method == "random_forest":
                forecast = issue_tree_forecast(records, target=body.target, issue_at_utc=body.issue_at_utc,
                                                intervals=intervals, site_timezone=site.timezone, seed=body.seed)
            else:
                forecast = issue_forecast(records, target=body.target, method=body.method,
                                          issue_at_utc=body.issue_at_utc, intervals=intervals,
                                          site_timezone=site.timezone)
        except ValueError as exc:
            raise _error("forecast_unavailable", str(exc)) from exc
        forecast_id = _new_id()
        payload = {"schema_version": "1", "forecast_id": forecast_id, "dataset_id": body.dataset_id,
                   "forecast": jsonable_encoder(forecast), "synthetic": data["synthetic"]}
        store.put("forecast", forecast_id, payload)
        return payload

    @app.post("/v1/sites/{site_id}/forecast-decision-studies", status_code=201)
    def create_forecast_decision_study(site_id: str, body: ForecastStudyInput):
        data = dataset_for(site_id, body.dataset_id)
        if not data["synthetic"] or "truth" not in data:
            raise _error("truth_unavailable", "decision regret requires synthetic truth for replay")
        truth = tuple(truth_from_dict(item) for item in data["truth"])
        if body.issue_index + body.horizon_intervals > len(truth):
            raise _error("invalid_horizon", "issue and evaluation horizon must fit the dataset",
                         field="horizon_intervals")
        site = site_from_dict(data["site_snapshot"])
        observed = tuple(record_from_dict(item) for item in data["records"])
        future = truth[body.issue_index:body.issue_index + body.horizon_intervals]
        outcomes = compare_forecast_decisions(site, observed, future,
            issue_at_utc=future[0].interval.start, objective=ObjectiveConfig("peak"), seed=body.seed)
        run_id = _new_id()
        status = "succeeded" if any(item.realized_objective is not None for item in outcomes) else "unavailable"
        payload = {"schema_version": "1", "run_id": run_id, "kind": "forecast_decision_study",
                   "site_id": site_id, "dataset_id": body.dataset_id, "status": status,
                   "synthetic": True, "truth_sha256": data["truth_sha256"],
                   "issue_index": body.issue_index, "issue_at_utc": future[0].interval.start.isoformat(),
                   "evaluation_end_utc": future[-1].interval.end.isoformat(),
                   "horizon_intervals": body.horizon_intervals, "seed": body.seed,
                   "objective_profile": "peak", "objective_unit": "kW",
                   "methods": jsonable_encoder(outcomes),
                   "reliability": "unknown",
                   "limitation": "Synthetic future truth is used only for scoring and the oracle comparator; "
                                 "field forecast accuracy and response reliability are unknown."}
        store.put("run", run_id, payload)
        return payload

    @app.post("/v1/sites/{site_id}/flexibility-assessments", status_code=201)
    def create_assessment(site_id: str, body: AssessmentInput):
        data = dataset_for(site_id, body.dataset_id)
        if not data["synthetic"] or "truth" not in data:
            raise _error("truth_unavailable", "an observed-only dataset cannot be scored as known truth")
        site = site_from_dict(data["site_snapshot"])
        truth = tuple(truth_from_dict(item) for item in data["truth"])
        run_id = _new_id()
        try:
            baseline = build_baseline(site, tuple(item.interval for item in truth), policy="B0")
            result = assess_envelope(site, truth, baseline.schedule, seed=body.seed,
                                     start_index=body.start_index, duration_intervals=body.duration_intervals,
                                     direction=body.direction)
            operational = result.pass_for("operational")
            status = "succeeded" if operational.status == "optimal" else "infeasible"
            payload = {"schema_version": "1", "run_id": run_id, "kind": "flexibility_assessment",
                       "site_id": site_id, "dataset_id": body.dataset_id,
                       "status": status, "synthetic": True, "truth_sha256": data["truth_sha256"],
                       "direction": body.direction, "start_index": body.start_index,
                       "duration_intervals": body.duration_intervals, "seed": body.seed,
                       "passes": jsonable_encoder(result.passes),
                       "reliable_kw": None, "method": result.method,
                       "recovery_import_delta_kwh": result.recovery_import_delta_kwh,
                       "schedule": [schedule_to_dict(item) for item in result.operational_schedule] if result.operational_schedule else None}
        except (ValueError, InfeasibleSchedule) as exc:
            payload = {"schema_version": "1", "run_id": run_id, "kind": "flexibility_assessment",
                       "site_id": site_id, "dataset_id": body.dataset_id, "status": "infeasible",
                       "synthetic": True, "reason": str(exc), "reliable_kw": None,
                       "seed": body.seed}
        store.put("run", run_id, payload)
        return {"run_id": run_id, "status": payload["status"], "passes": payload.get("passes"),
                "reason": payload.get("reason")}

    @app.post("/v1/sites/{site_id}/optimization-runs", status_code=201)
    def create_optimization(site_id: str, body: OptimizationInput):
        data = dataset_for(site_id, body.dataset_id)
        if not data["synthetic"] or "truth" not in data:
            raise _error("truth_unavailable", "an observed-only dataset cannot be optimized with hidden truth")
        site = site_from_dict(data["site_snapshot"])
        truth = tuple(truth_from_dict(item) for item in data["truth"])
        try:
            config = ObjectiveConfig(body.objective_profile, tuple(body.import_tariff_inr_per_kwh),
                                     tuple(body.export_credit_inr_per_kwh), body.demand_charge_inr_per_kw,
                                     body.curtailment_penalty_inr_per_kwh,
                                     body.battery_throughput_penalty_inr_per_kwh)
            solved = solve_schedule(site, truth, config, seed=body.seed, time_limit_s=body.solver_limit_s)
        except ValueError as exc:
            raise _error("invalid_optimization", str(exc)) from exc
        run_id = _new_id()
        status = "succeeded" if solved.status == "optimal_validated" else "infeasible" if solved.status == "infeasible_or_failed" else "failed"
        payload = {"schema_version": "1", "run_id": run_id, "kind": "optimization",
                   "site_id": site_id, "dataset_id": body.dataset_id, "status": status,
                   "synthetic": True, "truth_sha256": data["truth_sha256"],
                   "objective_profile": body.objective_profile, "solver_status": solved.status,
                   "solver_termination": solved.termination, "solver_version": solved.solver_version,
                   "objective_value": solved.validation.recomputed_objective if solved.validation else None,
                   "objective_unit": "INR" if body.objective_profile == "cost" else "kW" if body.objective_profile == "peak" else "kWh",
                   "max_balance_residual_kw": solved.validation.maximum_balance_residual_kw if solved.validation else None,
                   "grid_import_kw": [item.flows.grid_import_kw for item in solved.validation.trajectory.steps] if solved.validation else None,
                   "battery_energy_kwh": [item.battery_energy_after_kwh for item in solved.validation.trajectory.steps] if solved.validation else None,
                   "schedule": [schedule_to_dict(item) for item in solved.schedule] if solved.schedule else None,
                   "reason": solved.message}
        store.put("run", run_id, payload)
        return {"run_id": run_id, "status": status, "solver_status": solved.status,
                "objective_value": payload["objective_value"], "objective_unit": payload["objective_unit"]}

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str):
        return stored("run", run_id)

    @app.get("/v1/runs/{run_id}/decision-brief")
    def get_decision_brief(run_id: str):
        run = stored("run", run_id)
        if run.get("kind") != "flexibility_assessment":
            raise _error("assessment_unavailable", "a flexibility assessment is required", 409)
        data = stored("dataset", run["dataset_id"])
        site = site_from_dict(data["site_snapshot"])
        return build_decision_brief(run, site)

    @app.get("/v1/runs/{run_id}/measurement-sensitivity")
    def get_measurement_sensitivity(run_id: str):
        run = stored("run", run_id)
        if run["kind"] != "flexibility_assessment" or run["status"] != "succeeded" or not run.get("schedule"):
            raise _error("assessment_unavailable", "a validated flexibility schedule is required", 409)
        if "seed" not in run:
            raise _error("seed_unavailable", "rerun the assessment to record its replay seed", 409)
        data = stored("dataset", run["dataset_id"])
        if not data["synthetic"] or "truth" not in data:
            raise _error("truth_unavailable", "measurement sensitivity needs synthetic truth")
        site = site_from_dict(data["site_snapshot"])
        truth = tuple(truth_from_dict(item) for item in data["truth"])
        baseline = build_baseline(site, tuple(item.interval for item in truth), policy="B0")
        schedule = tuple(schedule_from_dict(item) for item in run["schedule"])
        operational = next((item for item in run["passes"] if item["mode"] == "operational"), None)
        if operational is None or not operational.get("sustained_kw"):
            raise _error("response_unavailable", "positive operational response is required", 409)
        try:
            result = assess_measurement_sensitivity(
                site, truth, baseline.schedule, schedule, seed=run["seed"],
                promised_kw=operational["sustained_kw"], direction=run["direction"],
                start_index=run["start_index"], duration_intervals=run["duration_intervals"])
        except (ValueError, InfeasibleSchedule) as exc:
            raise _error("sensitivity_failed", str(exc)) from exc
        return {"schema_version": "1", "source_run_id": run_id,
                "truth_sha256": data["truth_sha256"], "synthetic": True,
                "result": jsonable_encoder(result)}

    @app.post("/v1/sites/{site_id}/scenarios", status_code=201)
    def create_scenario(site_id: str, body: ScenarioInput):
        dataset_for(site_id, body.dataset_id)
        scenario_id = _new_id()
        try:
            config = ScenarioConfig(scenario_id, body.dataset_id, body.grid_import_limit_kw,
                                    body.grid_export_limit_kw, body.battery_max_charge_kw,
                                    body.battery_max_discharge_kw, body.seed)
        except ValueError as exc:
            raise _error("invalid_scenario", str(exc)) from exc
        payload = {"schema_version": "1", "scenario_id": scenario_id, "site_id": site_id,
                   "config": asdict(config)}
        store.put("scenario", scenario_id, payload)
        return payload

    @app.post("/v1/sites/{site_id}/scenarios/{scenario_id}/compare", status_code=201)
    def compare_saved_scenario(site_id: str, scenario_id: str):
        saved = stored("scenario", scenario_id)
        if saved["site_id"] != site_id:
            raise _error("site_scenario_mismatch", "scenario does not belong to site", 404)
        config = ScenarioConfig(**saved["config"])
        data = dataset_for(site_id, config.dataset_id)
        if not data["synthetic"]:
            raise _error("truth_unavailable", "paired scenario needs synthetic truth")
        site = site_from_dict(data["site_snapshot"])
        truth = tuple(truth_from_dict(item) for item in data["truth"])
        try:
            outcome = compare_scenario(site, truth, data["truth_sha256"], config,
                                       objective=ObjectiveConfig("peak"))
        except ValueError as exc:
            raise _error("invalid_scenario", str(exc)) from exc
        run_id = _new_id()
        payload = {"schema_version": "1", "run_id": run_id, "kind": "scenario_comparison",
                   "site_id": site_id, "dataset_id": config.dataset_id, "status": "succeeded",
                   "synthetic": True, "outcome": jsonable_encoder(outcome)}
        store.put("run", run_id, payload)
        return payload

    @app.post("/v1/sites/{site_id}/scenarios/{scenario_id}/stress-aware-compare", status_code=201)
    def compare_stress_aware(site_id: str, scenario_id: str):
        saved = stored("scenario", scenario_id)
        if saved["site_id"] != site_id:
            raise _error("site_scenario_mismatch", "scenario does not belong to site", 404)
        config = ScenarioConfig(**saved["config"])
        data = dataset_for(site_id, config.dataset_id)
        if not data["synthetic"] or "truth" not in data:
            raise _error("truth_unavailable", "stress-aware study needs synthetic truth")
        site = site_from_dict(data["site_snapshot"])
        truth = tuple(truth_from_dict(item) for item in data["truth"])
        training, evaluation = declared_stress_sets(site)
        try:
            outcome = select_stress_aware_schedule(site, truth, config, training, evaluation)
        except ValueError as exc:
            raise _error("invalid_stress_study", str(exc)) from exc
        run_id = _new_id()
        outcome_payload = jsonable_encoder(outcome)
        outcome_payload.pop("selected_schedule", None)
        payload = {"schema_version": "1", "run_id": run_id, "kind": "stress_aware_comparison",
                   "site_id": site_id, "dataset_id": config.dataset_id,
                   "status": "succeeded" if outcome.status == "selected" else "infeasible",
                   "synthetic": True, "truth_sha256": data["truth_sha256"],
                   "training_stresses": [asdict(item) for item in training],
                   "evaluation_stresses": [asdict(item) for item in evaluation],
                   "schedule": [schedule_to_dict(item) for item in outcome.selected_schedule]
                               if outcome.selected_schedule else None,
                   "outcome": outcome_payload}
        store.put("run", run_id, payload)
        return payload

    @app.post("/v1/experiments", status_code=201)
    def create_experiment(body: ExperimentInput):
        # Protocol IDs resolve to checked-in JSON specs, never arbitrary file paths.
        safe_id = Path(body.protocol_id).name
        if safe_id != body.protocol_id or not safe_id.endswith(".json"):
            raise _error("invalid_protocol", "protocol_id must name a checked-in JSON protocol")
        project_root = Path(__file__).resolve().parents[4]
        spec_path = project_root / "configs" / "experiments" / safe_id
        if not spec_path.exists():
            raise _error("protocol_not_found", "checked-in protocol not found", 404)
        try:
            spec = load_spec(spec_path)
            spec = type(spec)(**{**asdict(spec), "seeds": tuple(body.seed_set),
                                 "observation_variants": spec.observation_variants})
            runs = run_experiment(spec, project_root / ".local" / "experiments")
        except ValueError as exc:
            raise _error("experiment_invalid", str(exc)) from exc
        experiment_id = _new_id()
        payload = {"schema_version": "1", "experiment_id": experiment_id, "status": "succeeded",
                   "protocol_id": safe_id, "runs": jsonable_encoder(runs), "synthetic": True}
        store.put("experiment", experiment_id, payload)
        return {"experiment_id": experiment_id, "status": "succeeded", "run_ids": [run["run_id"] for run in runs]}

    @app.get("/v1/experiments/{experiment_id}")
    def get_experiment(experiment_id: str):
        return stored("experiment", experiment_id)

    @app.get("/v1/recommendations")
    def get_recommendation(run_id: str):
        run = stored("run", run_id)
        if run["kind"] != "optimization" or run["status"] != "succeeded":
            return {"schema_version": "1", "run_id": run_id, "status": "no_action",
                    "reason": "No independently validated optimized schedule is available."}
        data = stored("dataset", run["dataset_id"])
        site = site_from_dict(data["site_snapshot"])
        truth = tuple(truth_from_dict(item) for item in data["truth"])
        try:
            baseline_plan = build_baseline(site, tuple(item.interval for item in truth), policy="B0")
            baseline = simulate(site, truth, 7, baseline_plan.schedule)
        except (ValueError, InfeasibleSchedule) as exc:
            return {"schema_version": "1", "run_id": run_id, "status": "no_action",
                    "reason": f"Valid baseline unavailable: {exc}"}
        baseline_peak = max(item.flows.grid_import_kw for item in baseline.steps)
        optimized_peak = max(run["grid_import_kw"])
        reduction = baseline_peak - optimized_peak
        if reduction <= 1e-6:
            return {"schema_version": "1", "run_id": run_id, "status": "no_action",
                    "reason": "No positive simulated peak reduction against B0."}
        return {"schema_version": "1", "run_id": run_id, "status": "research_candidate",
                "action": "Review the validated 15-minute schedule before any operator decision.",
                "baseline_peak_kw": baseline_peak, "optimized_peak_kw": optimized_peak,
                "simulated_peak_reduction_kw": reduction, "reliability": "unknown",
                "provenance": "synthetic", "schedule_run_id": run_id}

    @app.get("/v1/reports/{run_id}")
    def get_report(run_id: str, format: str = "json"):
        run = stored("run", run_id)
        dataset = stored("dataset", run["dataset_id"])
        site = stored("site", run["site_id"])
        quality = next((item for item in reversed(store.list("quality_report"))
                        if item["dataset_id"] == run["dataset_id"]), None)
        recommendation = get_recommendation(run_id) if run["kind"] == "optimization" else None
        operational = next((item for item in run.get("passes", [])
                            if item["mode"] == "operational"), None)
        sensitivity = (get_measurement_sensitivity(run_id)
                       if run["kind"] == "flexibility_assessment" and run["status"] == "succeeded"
                       and "seed" in run and operational and operational.get("sustained_kw") else None)
        report = make_report(run, dataset, site, quality_report=quality,
                             recommendation=recommendation,
                             measurement_sensitivity=sensitivity)
        if format == "markdown":
            return PlainTextResponse(render_markdown(report), media_type="text/markdown")
        if format != "json":
            raise _error("invalid_format", "format must be json or markdown")
        return report

    built_frontend = Path(__file__).resolve().parents[4] / "frontend" / "dist"
    if (built_frontend / "index.html").is_file():
        app.mount("/", StaticFiles(directory=built_frontend, html=True), name="frontend")
    return app


app = create_app()
