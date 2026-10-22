"""Print a reproducible synthetic truth/observation summary (no real site data)."""

from datetime import datetime, timezone

from energy_lab.core.assets import GridConfig, PVConfig, SiteConfig
from energy_lab.simulation.generator import EVBehavior, GenerationConfig, generate_truth
from energy_lab.simulation.observer import ObservationConfig, observe_truth


site = SiteConfig("example-campus", "Asia/Kolkata", GridConfig(250, 50), PVConfig(100))
truth = generate_truth(GenerationConfig(
    dataset_id="example-truth-v1",
    site=site,
    start_utc=datetime(2025, 12, 31, 18, 30, tzinfo=timezone.utc),
    interval_count=96,
    root_seed=2026,
    ev_behavior=EVBehavior(2, 10, 8, 25),
))
observed = observe_truth(truth, ObservationConfig(
    dataset_id="example-observed-v1",
    root_seed=2027,
    interval_minutes=60,
    visible_quantities=("pv_available_kw", "critical_load_kw", "fixed_load_kw"),
    missing_blocks=((8, 2),),
))

print("SIMULATION DATA ONLY")
print(f"truth intervals: {len(truth.disturbances)}; EV sessions: {len(truth.site.evs)}")
print(f"observed records: {len(observed.observed.records)}")
print(f"truth sha256: {truth.manifest.truth_sha256}")
print(f"observed sha256: {observed.observed.manifest.observed_sha256}")
