"""Run the executable uncertainty audit and retain explicit evidence gaps.

Usage: PYTHONPATH=backend/src .venv/bin/python scripts/run_full_uncertainty_matrix.py --output-dir PATH
The observed-load benchmark is the frozen, provenance-labelled public snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from energy_lab.experiments.runner import load_spec, run_experiment
from energy_lab.experiments.synthetic_matrix import run_synthetic_matrix


ROOT = Path(__file__).resolve().parents[1]
OBSERVATION_SPEC = ROOT / "configs/experiments/paired_observation_stress.json"
PUBLIC_SUMMARY = ROOT / "configs/public_benchmarks/iblend_academic_summary.json"


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False, default=str) + "\n",
                    encoding="utf-8")


def main(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    physical = run_synthetic_matrix()
    observation = run_experiment(load_spec(OBSERVATION_SPEC), output_dir / "paired-observation-stress")
    public = json.loads(PUBLIC_SUMMARY.read_text(encoding="utf-8"))
    input_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (ROOT / "backend/src/energy_lab/experiments/synthetic_matrix.py",
                                 ROOT / "backend/src/energy_lab/uncertainty/scenarios.py",
                                 OBSERVATION_SPEC, PUBLIC_SUMMARY)}
    by_factor: dict[str, Counter] = defaultdict(Counter)
    for row in physical["rows"]:
        by_factor[row["factor"]][row["status"]] += 1
    by_variant: dict[str, Counter] = defaultdict(Counter)
    for run in observation:
        for result in run["results"]:
            variant = result["observation_dataset_id"].removeprefix("paired-observation-stress-").removesuffix(f"-{run['seed']}")
            by_variant[variant][result["status"]] += 1
    summary = {
        "schema_version": "1", "title": "FlexGrid uncertainty evidence matrix",
        "input_sha256": input_hashes,
        "synthetic_physical": {"evidence_label": physical["evidence_label"],
            "directions": physical["directions"], "response_durations_hours": physical["response_durations_hours"],
            "seeds": physical["seeds"], "row_count": len(physical["rows"]),
            "statuses": dict(Counter(row["status"] for row in physical["rows"])),
            "by_factor": {name: dict(counts) for name, counts in by_factor.items()}},
        "paired_observation": {"evidence_label": "paired synthetic hidden truth and corrupted observation",
            "seeds": [run["seed"] for run in observation], "variant_count": len(by_variant),
            "by_variant": {name: dict(counts) for name, counts in by_variant.items()},
            "truth_sha256_by_seed": {str(run["seed"]): run["truth_sha256"] for run in observation}},
        "public_observed_load": {"source": public["source"], "target": public["target"],
            "complete_intervals": public["aggregation"]["complete_intervals"],
            "expected_intervals": public["aggregation"]["expected_intervals"],
            "held_out_days": len(public["held_out_issues_utc"]),
            "condition_method_summaries": len(public["conditions"]),
            "evidence_label": "observed building mains forecast; injected sensor stresses are synthetic"},
        "claim_status": {"model_physical_stress": "executed_synthetic",
            "external_load_forecast_benchmark": "executed_observed_load",
            "thermal_comfort_response": "unknown",
            "applicable_tariff_cost_regret": "unknown",
            "measured_site_savings": "unknown",
            "field_flexibility_reliability": "unknown",
            "operator_acceptance": "unknown"},
        "limitations": ["A public meter from another building cannot validate this site's flexibility delivery.",
                        "The physical matrix uses a declared fixed schedule and synthetic disturbances.",
                        "Paired observation runs use another synthetic site without PV or flexible service logs.",
                        "Thermal comfort, tariff economics, seasonal coverage and operator acceptance require separate evidence."]}
    detail = {"summary": summary, "physical_rows": physical["rows"],
              "paired_observation_runs": observation, "public_observed_conditions": public["conditions"]}
    _write(output_dir / "uncertainty-matrix.json", detail)
    _write(output_dir / "uncertainty-matrix-summary.json", summary)
    lines = ["# FlexGrid uncertainty evidence matrix", "",
             "This is an executable model audit, not a field pilot. Input file SHA-256 values are in the JSON summary.", "",
             "## Evidence", "",
             f"- Synthetic physical replay: {len(physical['rows'])} cases, both import-response directions, 1/2/4-hour commitments, three declared seeds.",
             f"- Paired synthetic observation stress: {len(by_variant)} variants × {len(observation)} seeds, with hidden truth excluded from decisions.",
             f"- Public observed load: {summary['public_observed_load']['complete_intervals']}/{summary['public_observed_load']['expected_intervals']} complete 15-minute intervals and {summary['public_observed_load']['held_out_days']} held-out days from IIIT Delhi I-BLEND.",
             "", "## Physical replay by factor", "",
             "Statuses count individual direction × duration × seed cases. Infeasible cases are retained, not converted to zero response.", "",
             "| Factor | Delivered | Overstated | Baseline infeasible | Candidate infeasible | Not evaluable |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, counts in by_factor.items():
        lines.append(f"| {name} | {counts['delivered']} | {counts['overstated']} | {counts['baseline_infeasible']} | {counts['candidate_infeasible']} | {counts['not_evaluable']} |")
    lines += ["", "## Paired synthetic observation stress", "",
              "| Variant | Delivered | Overstated | Abstained | Other |", "|---|---:|---:|---:|---:|"]
    for name, counts in by_variant.items():
        other = sum(value for status, value in counts.items() if status not in {"delivered", "overstated", "abstained"})
        lines.append(f"| {name} | {counts['delivered']} | {counts['overstated']} | {counts['abstained']} | {other} |")
    lines += ["", "## Claims requiring field evidence", ""]
    for claim, status in summary["claim_status"].items():
        lines.append(f"- {claim.replace('_', ' ').capitalize()}: **{status.replace('_', ' ')}**.")
    lines += ["", "The public observed-data source is [I-BLEND](https://springernature.figshare.com/articles/dataset/Energy_dataset_of_IIITD/6007637) (CC0, DOI 10.6084/m9.figshare.6007637.v1). It does not contain verified site-wide import, PV, battery SOC, EV/pump/HVAC service, applicable tariff, or operator sign-off.",
              "", "For row-level reasons and energy-balance residuals, inspect `uncertainty-matrix.json`. For observed forecast errors, inspect the public benchmark report. No field reliability percentage is calculated.", ""]
    (output_dir / "uncertainty-matrix.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_dir / 'uncertainty-matrix.md'}")
    print(f"Physical cases: {len(physical['rows'])}; observation variants: {len(by_variant)}; public forecast summaries: {len(public['conditions'])}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(".local/uncertainty_matrix"))
    args = parser.parse_args()
    main(args.output_dir)
