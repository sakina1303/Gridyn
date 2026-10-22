"""JSON-configured paired synthetic experiment runner with separate artifacts."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import highspy
import pyomo

from energy_lab.data.manifest import canonical_sha256
from energy_lab.data.serde import record_to_dict, site_from_dict, truth_to_dict
from energy_lab.simulation.generator import GENERATOR_VERSION, GenerationConfig, generate_truth
from energy_lab.simulation.observer import ObservationConfig, observe_truth

from .ablations import run_paired_ablation


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    experiment_id: str
    hypothesis_id: str
    site: dict
    start_utc: str
    interval_count: int
    seeds: tuple[int, ...]
    observation_variants: tuple[dict, ...]
    issue_index: int
    horizon_intervals: int
    response_start_index: int
    response_duration_intervals: int
    direction: str

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.hypothesis_id or not self.seeds:
            raise ValueError("experiment ID, hypothesis and seeds are required")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("experiment seeds must be unique")
        ids = [item.get("id") for item in self.observation_variants]
        if not ids or any(not value for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("observation variant IDs must be unique and nonempty")


def load_spec(path: Path) -> ExperimentSpec:
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["seeds"] = tuple(raw["seeds"])
    raw["observation_variants"] = tuple(raw["observation_variants"])
    return ExperimentSpec(**raw)


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2, default=str, allow_nan=False) + "\n",
                    encoding="utf-8")


def run_experiment(spec: ExperimentSpec, output_root: Path) -> tuple[dict, ...]:
    site = site_from_dict(spec.site)
    start = datetime.fromisoformat(spec.start_utc.replace("Z", "+00:00"))
    config_hash = canonical_sha256(asdict(spec))
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                           stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"
    output_root.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    for seed in spec.seeds:
        run_id = canonical_sha256({"experiment": spec.experiment_id, "config": config_hash, "seed": seed})[:16]
        run_dir = output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        generated = generate_truth(GenerationConfig(
            f"{spec.experiment_id}-truth-{seed}", site, start, spec.interval_count, seed))
        configs = tuple(ObservationConfig(
            dataset_id=f"{spec.experiment_id}-{variant['id']}-{seed}", root_seed=seed,
            interval_minutes=variant.get("interval_minutes", 15),
            missing_probability=variant.get("missing_probability", 0),
            missing_blocks=tuple(tuple(block) for block in variant.get("missing_blocks", [])),
            power_noise_std_kw=variant.get("power_noise_std_kw", 0),
            power_bias_fraction=variant.get("power_bias_fraction", 0),
        ) for variant in spec.observation_variants)
        results = run_paired_ablation(generated, configs,
            issue_at_utc=generated.disturbances[spec.issue_index].interval.start,
            horizon_intervals=spec.horizon_intervals,
            start_index=spec.response_start_index,
            duration_intervals=spec.response_duration_intervals,
            direction=spec.direction, seed=seed)
        _write_json(run_dir / "truth.json", [truth_to_dict(item) for item in generated.disturbances])
        for config in configs:
            observed = observe_truth(generated, config).observed
            _write_json(run_dir / f"observed-{config.dataset_id}.json",
                        [record_to_dict(item) for item in observed.records])
        manifest = {"run_id": run_id, "experiment_id": spec.experiment_id,
                    "hypothesis_id": spec.hypothesis_id,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "code_revision": revision, "canonical_model_version": "46-v1",
                    "generator_version": GENERATOR_VERSION,
                    "pyomo_version": pyomo.version.version,
                    "solver_version": highspy.Highs().version(),
                    "config_sha256": config_hash,
                    "truth_sha256": generated.manifest.truth_sha256,
                    "seed": seed,
                    "forecast_issue_utc": generated.disturbances[spec.issue_index].interval.start.isoformat(),
                    "results": [asdict(item) for item in results],
                    "synthetic": True}
        _write_json(run_dir / "manifest.json", manifest)
        summaries.append(manifest)
    return tuple(summaries)
