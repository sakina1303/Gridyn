"""Plain Markdown export from the validated report schema."""

from __future__ import annotations


def render_markdown(report: dict) -> str:
    site = report["sections"]["site_and_period"]
    lines = ["# Energy Lab research report", "", f"**{report['headline_label']}**", "",
             f"Status: **{report['status']}**  ",
             f"Site: {site['site_name']} (`{report['site_id']}`)  ",
             f"Period: {site['start_utc']} to {site['end_utc']} ({site['timezone']})  ",
             f"Resolution: {site['interval_minutes']} minutes", "", "## Data and provenance", "",
             f"Dataset: `{report['dataset_id']}`  ",
             f"Checksum: `{report['dataset_hashes'][report['dataset_id']]}`  ",
             f"Run: `{report['run_ids'][0]}`  ",
             f"Canonical model: `{report['canonical_model_version']}`", "",
             "## Baseline and method", "", report["sections"]["baseline"]["definition"], ""]
    if report["metrics"]:
        lines += ["## Validated metrics", ""]
        for metric in report["metrics"]:
            lines.append(f"- **{metric['name'].replace('_', ' ').title()}**: {metric['value']:.6g} {metric['unit']} "
                         f"({metric['status']}; {metric['calculation']}; run `{metric['run_id']}`)")
        lines.append("")
    else:
        lines += ["## Validated metrics", "", "No numeric result is available for this run.", ""]
    envelope = report["sections"].get("envelope")
    if envelope is not None:
        lines += ["## Flexibility envelope", "",
                  "Values are sustained kW over the stated response and recovery horizon. Tested reliability: unknown.", ""]
        for item in envelope:
            lines.append(f"- {item['mode']}: {item['status']}; "
                         f"{item['sustained_kw'] if item['sustained_kw'] is not None else 'unavailable'} kW")
        lines.append("")
    optimization = report["sections"].get("optimization")
    if optimization is not None:
        lines += ["## Optimization", "", f"Solver status: {optimization['status']}  ",
                  f"Termination: {optimization['termination']}  ",
                  f"Solver version: {optimization['solver_version']}", ""]
    if report["sections"].get("recommendation"):
        recommendation = report["sections"]["recommendation"]
        lines += ["## Recommendation", "", recommendation.get("action") or recommendation.get("reason", "No action"), ""]
    if report["sections"].get("failed_or_infeasible"):
        lines += ["## Failure or infeasibility", "", report["sections"]["failed_or_infeasible"], ""]
    lines += ["## Next measurements", ""]
    measurements = report["sections"].get("next_measurements") or []
    lines += [f"- {item}" for item in measurements] if measurements else ["No quality report is attached to this run."]
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in report["limitations"]]
    lines += ["", "## Reproducibility", "", f"Report ID: `{report['report_id']}`", ""]
    return "\n".join(lines)
