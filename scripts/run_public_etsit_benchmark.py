"""Reproduce paired observed campus building load/PV forecast checks.

Source: CODECO/ETSIT Building C (Zenodo 19006030, CC BY 4.0). One-minute
W readings are averaged only when all 15 minutes in an interval are valid.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from energy_lab.experiments.paired_public_data import evaluate_paired_series
from energy_lab.experiments.public_benchmark import aggregate_minutes


SOURCE_URL = "https://zenodo.org/records/19006030"
MIRROR_URL = ("https://gitlab.eclipse.org/eclipse-research-labs/codeco-project/datasets/"
              "energy-demand-management/-/raw/main/datasets_2019/edificio_C_pro_power_2019.csv")
PUBLISHER_MD5 = "ad32daf43040ff243c05d60d0014cc4e"
START = datetime.fromtimestamp(1546297200, timezone.utc)  # 2019-01-01 00:00 local, UTC+1
DAYS = 41


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_source(path: Path) -> tuple[dict, dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Download the publisher's Building C CSV from {SOURCE_URL} to {path}")
    md5 = _digest(path, "md5")
    if md5 != PUBLISHER_MD5:
        raise ValueError("source MD5 does not match the Zenodo publisher record")
    end = START + timedelta(days=DAYS)
    selected: dict[int, tuple[str, str]] = {}
    load_conflicts: set[int] = set()
    pv_conflicts: set[int] = set()
    count = 0
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"unix_ref", "L_Tot", "PV_Tot"}.issubset(reader.fieldnames or ()):
            raise ValueError("documented Building C columns changed")
        for row in reader:
            raw_timestamp = row["unix_ref"]
            if not raw_timestamp.isdecimal():
                continue
            stamp = int(raw_timestamp)
            if stamp >= end.timestamp():
                break
            if stamp < START.timestamp():
                continue
            count += 1
            current = (row["L_Tot"], row["PV_Tot"])
            previous = selected.get(stamp)
            if previous is None:
                selected[stamp] = current
            else:
                if previous[0] != current[0]:
                    load_conflicts.add(stamp)
                if previous[1] != current[1]:
                    pv_conflicts.add(stamp)
    load_rows = [(str(stamp), "" if stamp in load_conflicts else values[0])
                 for stamp, values in selected.items()]
    pv_rows = [(str(stamp), "" if stamp in pv_conflicts else values[1])
               for stamp, values in selected.items()]
    load = aggregate_minutes(load_rows, start_utc=START, end_utc=end,
                             quantity="building_load_kw")
    pv = aggregate_minutes(pv_rows, start_utc=START, end_utc=end,
                           quantity="pv_output_kw")
    if load.expected_intervals != pv.expected_intervals:
        raise ValueError("paired windows do not align")
    load_lookup = {record.interval.start: record.value for record in load.records}
    pv_lookup = {record.interval.start: record.value for record in pv.records}
    instants = (START + timedelta(minutes=15 * index) for index in range(load.expected_intervals))
    times = tuple(instants)
    paired = {"building_load_kw": tuple(load_lookup.get(instant) for instant in times),
              "pv_output_kw": tuple(pv_lookup.get(instant) for instant in times)}
    quality = {"source_rows_in_window": count, "unique_source_minutes": len(selected),
               "duplicate_source_rows": count - len(selected),
               "conflicting_duplicate_minutes": {"building_load_kw": len(load_conflicts),
                                                 "pv_output_kw": len(pv_conflicts)},
               "expected_intervals": load.expected_intervals,
               "complete_intervals": {"building_load_kw": load.complete_intervals,
                                      "pv_output_kw": pv.complete_intervals},
               "invalid_source_rows": {"building_load_kw": load.invalid_source_rows,
                                       "pv_output_kw": pv.invalid_source_rows},
               "duplicate_source_minutes": {"building_load_kw": load.duplicate_source_minutes,
                                            "pv_output_kw": pv.duplicate_source_minutes}}
    source = {"url": SOURCE_URL, "mirror_url": MIRROR_URL, "doi": "10.5281/zenodo.19006030",
              "license": "CC BY 4.0", "published_channel_description":
              "ETSIT Building C total electrical load and total PV generation, W at 1-minute timestamps",
              "source_timezone": "Europe/Madrid; source unix_ref UTC and local date/time UTC+1 during selected winter window",
              "publisher_md5_verified": md5, "source_sha256": _digest(path, "sha256")}
    return paired, {"quality": quality, "source": source}


def run(path: Path) -> dict:
    paired, metadata = read_source(path)
    # Slots 40-59 are 10:00-15:00 local in this fixed UTC+1 winter window.
    # Full-day PV checks would be dominated by negative nighttime meter offsets.
    study = evaluate_paired_series(paired, first_test_day=34, test_days=7,
                                   evaluation_windows={"pv_output_kw": (40, 60)})
    return {"schema_version": "1", "title": "ETSIT Building C measured load/PV forecast benchmark",
            "source": metadata["source"], "period_start_utc": START.isoformat(),
            "period_end_utc": (START + timedelta(days=DAYS)).isoformat(),
            "interval_minutes": 15, "aggregation": metadata["quality"],
            "held_out_day_indices": list(range(34, 41)),
            "conditions": study["summaries"], "folds": study["folds"],
            "field_reliability": None,
            "limitations": ["A single Spanish campus building supplies measured load and PV output, not a Gridyn site pilot.",
                            "One-minute power samples are arithmetic-mean proxies for each 15-minute interval; incomplete, conflicting duplicate or negative gross readings are not filled.",
                            "PV forecast scores cover only 10:00-15:00 local winter hours because nighttime PV readings include negative meter offsets; unscored hours remain unevaluated.",
                            "Grid import/export, PV availability or curtailment, battery SOC, EV/pump service and operator limits are not established.",
                            "Forecast error does not establish delivered flexibility, measured savings or field reliability for India."]}


def main(input_path: Path, output_dir: Path, summary_out: Path | None) -> None:
    result = run(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "etsit-paired-observed-benchmark.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    summary = {key: value for key, value in result.items() if key != "folds"}
    if summary_out is not None:
        summary_out.parent.mkdir(parents=True, exist_ok=True)
        summary_out.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
                               encoding="utf-8")
    lines = ["# Measured campus load/PV benchmark", "",
             f"Source: [ETSIT Building C]({SOURCE_URL}) (CC BY 4.0).",
             f"Period: {result['period_start_utc']} to {result['period_end_utc']}.",
             f"Publisher MD5 verified; source SHA-256 `{result['source']['source_sha256']}`.",
             f"Complete 15-minute load/PV intervals: {result['aggregation']['complete_intervals']} "
             f"of {result['aggregation']['expected_intervals']}.",
             "", "## Seven chronological held-out days", "",
             "Each method uses only a prior observed day. Missing training or test slots cause an abstention. PV is scored only 10:00-15:00 local; load uses the full day.",
             "", "| Signal | Method | Evaluated / 7 | MAE (kW) | Absolute scored-window peak error (kW) |",
             "|---|---|---:|---:|---:|"]
    for row in result["conditions"]:
        mae = "Unknown" if row["mean_mae_kw"] is None else f"{row['mean_mae_kw']:.3f}"
        peak = ("Unknown" if row["mean_absolute_scored_peak_error_kw"] is None
                else f"{row['mean_absolute_scored_peak_error_kw']:.3f}")
        lines.append(f"| {row['signal']} | {row['method']} | {row['evaluated_days']}/7 | {mae} | {peak} |")
    lines.extend(["", "## Claim boundary", ""] + [f"- {item}" for item in result["limitations"]] + [""])
    (output_dir / "etsit-paired-observed-benchmark.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_dir / 'etsit-paired-observed-benchmark.md'}")
    print(f"Coverage: {result['aggregation']['complete_intervals']}; held-out days: 7")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(".local/public_etsit/edificio_C_pro_power_2019.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path(".local/public_etsit"))
    parser.add_argument("--summary-out", type=Path)
    arguments = parser.parse_args()
    main(arguments.input, arguments.output_dir, arguments.summary_out)
