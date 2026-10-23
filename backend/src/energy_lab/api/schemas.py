"""Typed HTTP input models with explicit kW, kWh and UTC fields."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WindowInput(BaseModel):
    start: datetime
    end: datetime


class GridInput(BaseModel):
    import_limit_kw: float = Field(ge=0)
    export_limit_kw: float = Field(ge=0)


class PVInput(BaseModel):
    ac_capacity_kw: float = Field(ge=0)
    allow_curtailment: bool = True


class BatteryInput(BaseModel):
    nominal_capacity_kwh: float = Field(gt=0)
    min_soc_fraction: float = Field(ge=0, le=1)
    max_soc_fraction: float = Field(gt=0, le=1)
    initial_energy_kwh: float = Field(ge=0)
    max_charge_kw: float = Field(ge=0)
    max_discharge_kw: float = Field(ge=0)
    charge_efficiency: float = Field(gt=0, le=1)
    discharge_efficiency: float = Field(gt=0, le=1)
    min_terminal_energy_kwh: float | None = None
    max_ramp_kw_per_hour: float | None = Field(default=None, ge=0)


class EVInput(BaseModel):
    asset_id: str
    window: WindowInput
    required_energy_kwh: float = Field(ge=0)
    max_power_kw: float = Field(gt=0)
    charger_efficiency: float = Field(default=1, gt=0, le=1)
    max_ramp_kw_per_hour: float | None = Field(default=None, ge=0)


class PumpInput(BaseModel):
    asset_id: str
    window: WindowInput
    rated_power_kw: float = Field(gt=0)
    required_runtime_hours: float = Field(ge=0)
    minimum_run_intervals: int = Field(default=1, ge=1)


class HVACInput(BaseModel):
    asset_id: str
    windows: list[WindowInput]
    min_power_kw: float = Field(ge=0)
    max_power_kw: float = Field(ge=0)
    max_ramp_kw_per_hour: float | None = Field(default=None, ge=0)


class SiteCreate(BaseModel):
    schema_version: str = "1"
    name: str
    timezone: str
    grid: GridInput
    pv: PVInput
    battery: BatteryInput | None = None
    evs: list[EVInput] = Field(default_factory=list)
    pumps: list[PumpInput] = Field(default_factory=list)
    hvacs: list[HVACInput] = Field(default_factory=list)


class SyntheticCreate(BaseModel):
    schema_version: str = "1"
    start_utc: datetime
    interval_count: int = Field(default=96, ge=1, le=960)
    seed: int = 7
    weather_scenario: str = "clear"
    load_scenario: str = "normal"
    solar_scenario: str = "standard"
    critical_base_kw: float = Field(default=30, ge=0)
    fixed_base_kw: float = Field(default=45, ge=0)
    day_activity_kw: float = Field(default=45, ge=0)
    evening_activity_kw: float = Field(default=20, ge=0)
    cooling_kw_per_c_above_28: float = Field(default=2, ge=0)


class ValidateInput(BaseModel):
    schema_version: str = "1"
    claim_types: list[str] = Field(default_factory=list)
    tariff_verified: bool = False


class ForecastInput(BaseModel):
    schema_version: str = "1"
    dataset_id: str
    target: str
    issue_at_utc: datetime
    horizon_intervals: int = Field(ge=1, le=96)
    method: str = "previous_day"
    seed: int = 7


class ForecastStudyInput(BaseModel):
    schema_version: str = "1"
    dataset_id: str
    issue_index: int = Field(default=96, ge=96)
    horizon_intervals: int = Field(default=96, ge=1, le=96)
    seed: int = 7


class AssessmentInput(BaseModel):
    schema_version: str = "1"
    dataset_id: str
    start_index: int = Field(ge=0)
    duration_intervals: int = Field(ge=1)
    direction: str
    seed: int = 7


class OptimizationInput(BaseModel):
    schema_version: str = "1"
    dataset_id: str
    objective_profile: str
    import_tariff_inr_per_kwh: list[float] = Field(default_factory=list)
    export_credit_inr_per_kwh: list[float] = Field(default_factory=list)
    demand_charge_inr_per_kw: float = Field(default=0, ge=0)
    curtailment_penalty_inr_per_kwh: float = Field(default=0, ge=0)
    battery_throughput_penalty_inr_per_kwh: float = Field(default=0, ge=0)
    seed: int = 7
    solver_limit_s: float = Field(default=30, gt=0, le=300)


class ScenarioInput(BaseModel):
    schema_version: str = "1"
    dataset_id: str
    grid_import_limit_kw: float | None = Field(default=None, ge=0)
    grid_export_limit_kw: float | None = Field(default=None, ge=0)
    battery_max_charge_kw: float | None = Field(default=None, ge=0)
    battery_max_discharge_kw: float | None = Field(default=None, ge=0)
    seed: int = 7


class ExperimentInput(BaseModel):
    schema_version: str = "1"
    protocol_id: str
    seed_set: list[int] = Field(min_length=1)
