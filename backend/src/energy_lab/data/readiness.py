"""Claim-specific readiness; never turn missing evidence into a firm promise."""

from __future__ import annotations

from dataclasses import dataclass

from energy_lab.core.assets import SiteConfig

from .quality import DataQualityReport, SeriesQuality


VALID_STATES = frozenset({"usable", "usable_with_limitations", "insufficient", "invalid"})


@dataclass(frozen=True, slots=True)
class ClaimReadiness:
    claim: str
    state: str
    explanation: str
    next_measurement: str | None = None

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError("invalid readiness state")


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    claims: tuple[ClaimReadiness, ...]

    def for_claim(self, claim: str) -> ClaimReadiness:
        result = next((item for item in self.claims if item.claim == claim), None)
        if result is None:
            raise KeyError(claim)
        return result


def _series_state(series: SeriesQuality | None) -> str:
    return "insufficient" if series is None else series.status


def assess_readiness(
    quality: DataQualityReport,
    site: SiteConfig,
    *,
    evidence_kind: str,
    tariff_verified: bool = False,
) -> ReadinessReport:
    if evidence_kind not in {"synthetic", "observed"}:
        raise ValueError("evidence_kind must be synthetic or observed")
    claims: list[ClaimReadiness] = []
    has_flex = bool(site.battery or site.evs or site.pumps or site.hvacs)
    claims.append(ClaimReadiness(
        "theoretical_asset_flexibility",
        "usable_with_limitations" if has_flex else "insufficient",
        "Asset ratings and windows permit a theoretical bound, not a delivered response." if has_flex else "No flexible asset is configured.",
        None if has_flex else "Record a controllable asset, rating, and operating window.",
    ))

    grid = quality.for_quantity("grid_import_kw")
    if grid is None:
        claims.append(ClaimReadiness("measured_15min_peak", "insufficient", "No site import meter series is present.", "Collect 15-minute site import readings."))
    elif grid.status == "invalid":
        claims.append(ClaimReadiness("measured_15min_peak", "invalid", "Site import series has invalid timestamps, units, duplicates, or physical values.", "Resolve flagged import-meter records."))
    elif grid.resolution_minutes != 15 or grid.coverage < 1 or evidence_kind == "synthetic":
        claims.append(ClaimReadiness("measured_15min_peak", "insufficient", "A verified full-period measured 15-minute peak requires complete observed 15-minute import data.", "Collect or reconcile complete 15-minute site import data."))
    else:
        claims.append(ClaimReadiness("measured_15min_peak", "usable", "Complete observed 15-minute import series supports the study-period measured peak."))

    forecast_source = grid or quality.for_quantity("metered_building_load_kw") or quality.for_quantity("fixed_load_kw")
    days = (quality.expected_window.end - quality.expected_window.start).total_seconds() / 86400
    if forecast_source is None:
        claims.append(ClaimReadiness("historical_load_forecast", "insufficient", "No load or import series is present.", "Collect timestamped site import or load readings."))
    elif forecast_source.status == "invalid":
        claims.append(ClaimReadiness("historical_load_forecast", "invalid", "Forecast source series is invalid.", "Correct units, timestamps, and negative gross values."))
    elif days < 30 or forecast_source.coverage < 0.80:
        claims.append(ClaimReadiness("historical_load_forecast", "insufficient", "Below the provisional 30-day/80%-coverage backtest gate; seasonal reliability is unknown.", "Collect at least 30 representative days; longer seasonal history is preferable."))
    else:
        state = "usable_with_limitations" if evidence_kind == "synthetic" or forecast_source.coverage < 0.95 else "usable"
        claims.append(ClaimReadiness("historical_load_forecast", state, "A time-split forecast can be tested; generalization beyond the observed period is unproven."))

    if site.battery is None:
        claims.append(ClaimReadiness("firm_battery_response", "insufficient", "No battery is configured."))
    else:
        soc = quality.for_quantity("battery_soc_kwh")
        if soc is not None and soc.status == "invalid":
            claims.append(ClaimReadiness("firm_battery_response", "invalid", "Battery SOC observations are invalid.", "Reconcile battery SOC telemetry and units."))
        elif soc is None or soc.coverage < 1 or evidence_kind == "synthetic":
            claims.append(ClaimReadiness("firm_battery_response", "usable_with_limitations", "Battery rating and assumed initial SOC support scenarios, not a firm observed discharge promise.", "Collect timestamped battery SOC and AC power."))
        else:
            claims.append(ClaimReadiness("firm_battery_response", "usable_with_limitations", "SOC is observed, but deliverability still needs service and uncertainty validation."))

    pv_avail = quality.for_quantity("pv_available_kw")
    pv_used = quality.for_quantity("pv_used_kw")
    if any(item is not None and item.status == "invalid" for item in (pv_avail, pv_used)):
        claims.append(ClaimReadiness("measured_pv_utilization", "invalid", "PV series contains invalid records.", "Reconcile PV meter units and timestamps."))
    elif pv_avail is None or pv_used is None or evidence_kind == "synthetic":
        claims.append(ClaimReadiness("measured_pv_utilization", "insufficient", "Available and used PV must both be observed for a measured utilization claim.", "Collect separate PV available/used output or inverter curtailment data."))
    else:
        claims.append(ClaimReadiness("measured_pv_utilization", "usable_with_limitations", "PV utilization can be calculated on covered intervals; inspect missingness and curtailment interpretation."))

    claims.append(ClaimReadiness(
        "applicable_tariff_cost",
        "usable_with_limitations" if tariff_verified else "insufficient",
        "Tariff is marked verified, but bill rules still need review." if tariff_verified else "No verified applicable tariff/category is supplied; physical results remain valid.",
        None if tariff_verified else "Record the current state/category tariff order and demand/export terms.",
    ))
    claims.append(ClaimReadiness(
        "calibrated_reliable_response", "insufficient",
        "A response reliability claim requires held-out delivery tests; that layer is not implemented yet.",
        "Collect event outcomes or run documented held-out synthetic scenarios before reporting a tested fraction.",
    ))
    return ReadinessReport(tuple(claims))
