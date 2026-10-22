"""One-at-a-time synthetic measurement restoration comparisons.

An abstaining model has no numerical overstatement to improve. Keep that
distinction visible instead of assigning an invented zero-error score.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from energy_lab.simulation.observer import ALL_QUANTITIES, ObservationConfig, POWER_QUANTITIES

from .ablations import AblationResult


@dataclass(frozen=True, slots=True)
class MeasurementEffect:
    quantity: str
    without_dataset_id: str
    restored_dataset_id: str
    without_status: str
    restored_status: str
    assessment_enabled: bool
    overstatement_reduction_kw: float | None
    interval_width_reduction_kw: float | None
    evidence_label: str = "synthetic paired model sensitivity"


def compare_restorations(
    configs: tuple[ObservationConfig, ...], results: tuple[AblationResult, ...],
) -> tuple[MeasurementEffect, ...]:
    """Compare full observation with otherwise identical one-signal masks."""
    by_id = {result.observation_dataset_id: result for result in results}
    if len(by_id) != len(results):
        raise ValueError("observation results must have unique dataset IDs")
    full = [config for config in configs if set(config.visible_quantities) == set(ALL_QUANTITIES)]
    effects: list[MeasurementEffect] = []
    for masked in configs:
        absent = set(ALL_QUANTITIES) - set(masked.visible_quantities)
        if len(absent) != 1 or not absent <= set(POWER_QUANTITIES):
            continue
        matches = [candidate for candidate in full
                   if replace(masked, dataset_id=candidate.dataset_id,
                              visible_quantities=candidate.visible_quantities) == candidate]
        if not matches:
            continue
        if len(matches) != 1:
            raise ValueError("ambiguous full observation comparator")
        restored = matches[0]
        full_result = by_id.get(restored.dataset_id)
        if full_result is None:
            raise ValueError("full observation result is missing")
        masked_result = by_id.get(masked.dataset_id)
        if masked_result is None:
            raise ValueError("masked observation result is missing")
        if (masked_result.truth_sha256 != full_result.truth_sha256 or
                masked_result.issue_at_utc != full_result.issue_at_utc):
            raise ValueError("measurement comparison requires paired truth and issue time")
        reduction = None
        if (masked_result.overstatement_kw is not None and
                full_result.overstatement_kw is not None):
            reduction = masked_result.overstatement_kw - full_result.overstatement_kw
        effects.append(MeasurementEffect(
            quantity=next(iter(absent)), without_dataset_id=masked.dataset_id,
            restored_dataset_id=restored.dataset_id,
            without_status=masked_result.status, restored_status=full_result.status,
            assessment_enabled=masked_result.estimated_sustained_kw is None and
                               full_result.estimated_sustained_kw is not None,
            overstatement_reduction_kw=reduction,
            interval_width_reduction_kw=None,
        ))
    return tuple(sorted(effects, key=lambda item: item.quantity))
