"""Run a JSON protocol using the same experiment runner as the local API."""

from __future__ import annotations

import argparse
from pathlib import Path

from energy_lab.experiments.runner import load_spec, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".local/experiments"))
    args = parser.parse_args()
    runs = run_experiment(load_spec(args.spec), args.output)
    for run in runs:
        print(run["run_id"], run["truth_sha256"],
              [(item["observation_dataset_id"], item["status"]) for item in run["results"]])


if __name__ == "__main__":
    main()
