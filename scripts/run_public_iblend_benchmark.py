"""Fetch a bounded public I-BLEND slice and evaluate observational load forecasts.

Usage: PYTHONPATH=backend/src .venv/bin/python scripts/run_public_iblend_benchmark.py --output-dir PATH
The original archive is accessed with HTTP range requests; raw/private pilot data are not used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from energy_lab.experiments.public_benchmark import aggregate_minutes, evaluate_observed_forecasts


ARTICLE_URL = "https://api.figshare.com/v2/articles/6007637"
ARTICLE_DOI = "10.6084/m9.figshare.6007637.v1"
MEMBER = "energy_dataset/acad_build_mains.csv"
START = datetime(2013, 8, 9, 18, 30, tzinfo=timezone.utc)  # 2013-08-10 midnight IST
DAYS = 41


class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url: str, size: int):
        self.url, self.size, self.position = url, size, 0
        self.buffer_start, self.buffer = -1, b""

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = 0) -> int:
        self.position = (0 if whence == 0 else self.position if whence == 1 else self.size) + offset
        return self.position

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = self.size - self.position
        if size == 0:
            return b""
        if not (self.buffer_start <= self.position and
                self.position + size <= self.buffer_start + len(self.buffer)):
            end = min(self.size - 1, self.position + max(size, 2 * 1024 * 1024) - 1)
            request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.position}-{end}"})
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 206:
                    raise ValueError("source server did not honor bounded range request")
                self.buffer = response.read()
            self.buffer_start = self.position
        offset = self.position - self.buffer_start
        result = self.buffer[offset:offset + size]
        self.position += len(result)
        return result


def fetch_rows() -> tuple[list[tuple[str, str]], dict]:
    with urllib.request.urlopen(ARTICLE_URL, timeout=30) as response:
        metadata = json.load(response)
    if metadata.get("license", {}).get("name") != "CC0":
        raise ValueError("source reuse licence changed; review before continuing")
    source = next((item for item in metadata["files"] if item["name"] == "energy_dataset.zip"), None)
    if source is None:
        raise ValueError("expected public source archive is unavailable")
    end = START + timedelta(days=DAYS)
    rows: list[tuple[str, str]] = []
    sample_hash = hashlib.sha256()
    archive = HTTPRangeFile(source["download_url"], source["size"])
    with zipfile.ZipFile(archive) as zipped, zipped.open(MEMBER) as stream:
        reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8"))
        if not {"timestamp", "power"}.issubset(reader.fieldnames or ()):
            raise ValueError("documented source columns changed")
        for line in reader:
            raw_timestamp, raw_watts = line["timestamp"], line["power"]
            try:
                approximate = float(raw_timestamp)
            except ValueError:
                continue
            if approximate >= end.timestamp():
                break
            if approximate < START.timestamp():
                continue
            rows.append((raw_timestamp, raw_watts))
            sample_hash.update(f"{raw_timestamp},{raw_watts}\n".encode())
    provenance = {"article_url": metadata["url_public_html"], "article_doi": ARTICLE_DOI,
                  "collection_doi": "10.6084/m9.figshare.c.3893581.v1",
                  "source_file_id": source["id"], "source_archive_md5_from_publisher": source["computed_md5"],
                  "source_archive_md5_verified_locally": False,
                  "source_member": MEMBER, "selected_raw_rows_sha256": sample_hash.hexdigest(),
                  "license": "CC0", "measured_channel": "Academic building mains power, W",
                  "source_timezone": "Asia/Kolkata", "source_rows_in_window": len(rows)}
    return rows, provenance


def _summaries(folds: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in folds:
        groups[(item["condition"], item["method"])].append(item)
    summaries = []
    for (condition, method), items in groups.items():
        evaluated = [item for item in items if item["status"] == "evaluated"]
        summaries.append({"condition": condition, "method": method,
                          "factor": items[0]["factor"], "severity": items[0]["severity"],
                          "evaluated_folds": len(evaluated), "abstained_folds": len(items) - len(evaluated),
                          "mean_mae_kw": sum(item["mae_kw"] for item in evaluated) / len(evaluated) if evaluated else None,
                          "mean_absolute_peak_error_kw": sum(item["absolute_peak_error_kw"] for item in evaluated) / len(evaluated) if evaluated else None})
    return summaries


def main(output_dir: Path) -> None:
    rows, provenance = fetch_rows()
    end = START + timedelta(days=DAYS)
    aggregation = aggregate_minutes(rows, start_utc=START, end_utc=end)
    if aggregation.complete_intervals < 30 * 96 * 0.8:
        raise ValueError("public sample has insufficient 15-minute coverage for a 30-day study")
    lookup = {item.interval.start for item in aggregation.records}
    candidate_issues = (START + timedelta(days=day) for day in range(31, 40))
    issues = tuple(issue for issue in candidate_issues if all(
        issue + timedelta(minutes=15 * index) in lookup for index in range(96)))[:7]
    if len(issues) < 3:
        raise ValueError("fewer than three complete held-out days exist")
    study = evaluate_observed_forecasts(aggregation.records, issue_times_utc=issues)
    summaries = _summaries(study["folds"])
    payload = {"schema_version": "1", "title": "I-BLEND Academic building observed-load benchmark",
               "target": study["target"], "unit": study["unit"],
               "source": provenance, "period_start_utc": START.isoformat(),
               "period_end_utc": end.isoformat(), "interval_minutes": 15,
               "aggregation": {"expected_intervals": aggregation.expected_intervals,
                               "complete_intervals": aggregation.complete_intervals,
                               "missing_or_partial_intervals": aggregation.missing_or_partial_intervals,
                               "invalid_source_rows": aggregation.invalid_source_rows,
                               "duplicate_source_minutes": aggregation.duplicate_source_minutes},
               "held_out_issues_utc": [item.isoformat() for item in issues],
               "seeds": [7, 11, 19], "conditions": summaries,
               "folds": study["folds"], "limitations": study["limitations"]}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "iblend-observed-benchmark.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    summary = {key: value for key, value in payload.items() if key != "folds"}
    (output_dir / "iblend-observed-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    with (output_dir / "iblend-academic-15min.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("start", "end", "quantity", "value", "unit"))
        for item in aggregation.records:
            writer.writerow((item.interval.start.isoformat(), item.interval.end.isoformat(),
                             item.quantity, f"{item.value:.9f}", item.unit))
    lines = ["# Public observed-load benchmark", "", "**Observed Academic building mains meter, IIIT Delhi.**",
             "Injected sensor stresses are synthetic; this is not a FlexGrid pilot or flexibility validation.", "",
             f"Source: [I-BLEND energy dataset](https://springernature.figshare.com/articles/dataset/Energy_dataset_of_IIITD/6007637) ({ARTICLE_DOI}, CC0).",
             f"Period: {START.isoformat()} to {end.isoformat()} (Asia/Kolkata site timezone).",
             f"Complete 15-minute intervals: {aggregation.complete_intervals}/{aggregation.expected_intervals}; "
             f"partial or missing: {aggregation.missing_or_partial_intervals}.",
             f"Invalid raw rows: {aggregation.invalid_source_rows}; duplicate minutes: {aggregation.duplicate_source_minutes}.",
             f"Selected raw-row SHA-256: `{provenance['selected_raw_rows_sha256']}`.",
             "The source archive MD5 is publisher metadata and was not verified locally because only bounded ranges were transferred.",
             "", "## Chronological forecast stress study", "",
             "Seven complete held-out days; clean control once and three fixed seeds per perturbation; no future meter reading enters training.",
             "Error is for building mains load (kW), not delivered grid flexibility.", "",
             "| Condition | Method | Evaluated / total | MAE (kW) | Absolute peak error (kW) |", "|---|---|---:|---:|---:|"]
    for item in summaries:
        count = item["evaluated_folds"] + item["abstained_folds"]
        mae = f"{item['mean_mae_kw']:.3f}" if item["mean_mae_kw"] is not None else "Unknown"
        peak = f"{item['mean_absolute_peak_error_kw']:.3f}" if item["mean_absolute_peak_error_kw"] is not None else "Unknown"
        lines.append(f"| {item['condition']} | {item['method']} | {item['evaluated_folds']}/{count} | {mae} | {peak} |")
    lines += ["", "## Claim boundary", ""] + [f"- {item}" for item in study["limitations"]]
    lines += ["- No operator supplied asset limits, site import meter, applicable tariff, or consented pilot data.",
              "- Measured savings, response reliability, and operator acceptance remain Unknown.", ""]
    (output_dir / "iblend-observed-benchmark.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_dir / 'iblend-observed-benchmark.md'}")
    print(f"Complete intervals: {aggregation.complete_intervals}/{aggregation.expected_intervals}; "
          f"held-out days: {len(issues)}; condition-method summaries: {len(summaries)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(".local/public_iblend"))
    arguments = parser.parse_args()
    main(arguments.output_dir)
