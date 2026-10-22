"""Every displayed number has a unit, run, dataset and calculation reference."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class MetricValue:
    name: str
    value: float
    unit: str
    start_utc: str
    end_utc: str
    run_id: str
    dataset_id: str
    dataset_sha256: str
    provenance: str
    calculation: str
    status: str
    baseline_value: float | None = None
    delta: float | None = None

    def __post_init__(self) -> None:
        if not all((self.name, self.unit, self.start_utc, self.end_utc,
                    self.run_id, self.dataset_id, self.dataset_sha256,
                    self.provenance, self.calculation, self.status)):
            raise ValueError("report metric is missing a traceability field")


def make_report(run: dict, dataset: dict, site: dict, *, quality_report: dict | None = None,
                recommendation: dict | None = None) -> dict:
    if run.get("dataset_id") != dataset.get("dataset_id") or run.get("site_id") != site.get("site_id"):
        raise ValueError("report references do not resolve to the same site and dataset")
    if run.get("status") == "succeeded" and run.get("kind") == "optimization":
        if run.get("max_balance_residual_kw") is None or run.get("schedule") is None:
            raise ValueError("successful optimization lacks validated schedule or residual")
    checksum = dataset.get("truth_sha256") or dataset.get("observed_sha256")
    if not checksum:
        raise ValueError("dataset checksum is required")
    start, end = dataset["start_utc"], dataset["end_utc"]
    provenance = "synthetic" if dataset.get("synthetic") else "observed"
    metrics: list[MetricValue] = []
    if run.get("kind") == "optimization" and run.get("objective_value") is not None:
        metrics.append(MetricValue("optimized_objective", run["objective_value"],
            run["objective_unit"], start, end, run["run_id"], dataset["dataset_id"], checksum,
            provenance, f"independently replayed {run['objective_profile']} objective", "validated"))
        metrics.append(MetricValue("maximum_balance_residual", run["max_balance_residual_kw"],
            "kW", start, end, run["run_id"], dataset["dataset_id"], checksum,
            provenance, "maximum absolute physical balance residual over every 15-minute interval", "validated"))
    if run.get("kind") == "flexibility_assessment":
        for item in run.get("passes", []):
            if item.get("sustained_kw") is None:
                continue
            metrics.append(MetricValue(f"{item['mode']}_sustained_response", item["sustained_kw"],
                "kW", start, end, run["run_id"], dataset["dataset_id"], checksum,
                provenance, "joint sustained response against B0 over declared window and recovery horizon",
                item["status"]))
    if recommendation and recommendation.get("simulated_peak_reduction_kw") is not None:
        metrics.append(MetricValue("simulated_peak_reduction", recommendation["simulated_peak_reduction_kw"],
            "kW", start, end, run["run_id"], dataset["dataset_id"], checksum,
            provenance, "B0 peak minus independently replayed optimized peak", "validated",
            recommendation["baseline_peak_kw"], -recommendation["simulated_peak_reduction_kw"]))
    sections = {
        "site_and_period": {"site_name": site.get("name"), "site_id": site["site_id"],
                            "timezone": site["config"]["timezone"], "start_utc": start, "end_utc": end,
                            "interval_minutes": dataset["interval_minutes"]},
        "data_inventory": {"dataset_id": dataset["dataset_id"], "source": provenance,
                           "quality_report_id": quality_report.get("quality_report_id") if quality_report else None,
                           "readiness": quality_report.get("readiness") if quality_report else None},
        "asset_constraints": site["config"],
        "baseline": {"label": "B0", "definition": "Earliest declared EV/pump service, minimum HVAC power, battery idle."},
        "forecast_and_uncertainty": {"status": "unavailable_in_this_run",
                                     "reliability": "unknown", "reason": "No calibrated held-out reliability is attached."},
        "envelope": run.get("passes") if run.get("kind") == "flexibility_assessment" else None,
        "optimization": {"status": run.get("solver_status"), "termination": run.get("solver_termination"),
                         "solver_version": run.get("solver_version"),
                         "schedule_run_id": run["run_id"] if run.get("schedule") else None}
                         if run.get("kind") == "optimization" else None,
        "scenario_comparison": run.get("outcome") if run.get("kind") == "scenario_comparison" else None,
        "recommendation": recommendation,
        "failed_or_infeasible": run.get("reason") if run.get("status") != "succeeded" else None,
        "next_measurements": [item.get("next_measurement") for item in
                              (quality_report or {}).get("readiness", {}).get("claims", [])
                              if item.get("next_measurement")],
    }
    return {"schema_version": "1", "report_id": run["run_id"],
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": run["status"], "synthetic": bool(dataset.get("synthetic")),
            "headline_label": "SIMULATION DATA ONLY" if dataset.get("synthetic") else "OBSERVED DATA; ANALYTICAL CLAIMS LIMITED",
            "site_id": site["site_id"], "dataset_id": dataset["dataset_id"],
            "run_ids": [run["run_id"]], "dataset_hashes": {dataset["dataset_id"]: checksum},
            "canonical_model_version": "46-v1", "metrics": [asdict(item) for item in metrics],
            "sections": sections,
            "limitations": ["No physical control is performed.",
                            "Statistical response reliability is unknown without calibrated held-out evidence.",
                            "Synthetic results do not establish measured grid, cost or carbon benefits."]}
