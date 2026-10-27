"""Plain-language decision brief for a simulated flexibility assessment.

The brief describes validated model output without promoting an oracle result to
an operational commitment. Measurement requests are requirements, not an
estimated value-of-information or a procurement ranking.
"""

from __future__ import annotations

from energy_lab.core.assets import SiteConfig


def build_decision_brief(run: dict, site: SiteConfig) -> dict:
    if run.get("kind") != "flexibility_assessment":
        raise ValueError("decision brief requires a flexibility assessment")

    operational = next((item for item in run.get("passes", ())
                        if item["mode"] == "operational"), None)
    validated = (run.get("status") == "succeeded" and operational is not None
                 and operational.get("status") == "optimal"
                 and (operational.get("sustained_kw") or 0) > 0)
    constraints = ["physical power balance", "critical load service", "grid limits"]
    if site.battery:
        constraints.append("battery SOC and terminal requirement")
    if site.evs or site.pumps or site.hvacs:
        constraints.append("configured asset service windows")
    measurements = [
        {"signal": "Site grid import", "request": "Collect timestamped 15-minute site import readings and meter sign convention."},
    ]
    if site.pv.ac_capacity_kw > 0:
        measurements.append({"signal": "Solar PV", "request": "Collect timestamped PV output and available-generation or curtailment records."})
    if site.battery:
        measurements.append({"signal": "Battery", "request": "Collect timestamped SOC, AC charge/discharge power, availability and verified ratings."})
    if site.evs:
        measurements.append({"signal": "EV charging", "request": "Collect actual arrivals, departures and energy delivered by departure."})
    if site.pumps:
        measurements.append({"signal": "Pump service", "request": "Collect runtime and service-completion records within operating windows."})
    if site.hvacs:
        measurements.append({"signal": "HVAC comfort", "request": "Collect indoor temperature and operator-approved comfort limits; thermal comfort is not modeled yet."})

    return {
        "schema_version": "1",
        "source_run_id": run["run_id"],
        "dataset_id": run["dataset_id"],
        "evidence": "synthetic" if run.get("synthetic") else "observed",
        "status": "simulation_only" if validated else "no_validated_response",
        "response": {
            "direction": run.get("direction"),
            "sustained_kw": operational["sustained_kw"] if validated else None,
            "duration_hours": run.get("duration_intervals", 0) * 0.25 if validated else None,
            "recovery_import_delta_kwh": run.get("recovery_import_delta_kwh") if validated else None,
        },
        "constraints_checked": constraints,
        "binding_constraint": None,
        "binding_constraint_reason": "A binding-constraint attribution is not recorded by this assessment.",
        "field_reliability": None,
        "operational_use": "do_not_dispatch",
        "explanation": (
            "A physically validated response exists in a synthetic perfect-information scenario. "
            "It is not a field-tested promise."
            if validated else
            "No operational response was independently validated for this scenario."
        ),
        "failure_reason": None if validated else run.get("reason") or (operational or {}).get("solver_termination"),
        "next_measurements": measurements,
        "pilot_gate": ["Site permission and data handling agreement", "Observed site and asset records",
                       "Operator-approved service and comfort constraints", "Chronological shadow replay",
                       "Independent operator review"],
    }
