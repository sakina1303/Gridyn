"""Strict CSV normalization to UTC intervals and canonical units."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import datetime, timezone

from energy_lab.core.time import TimeInterval, local_to_utc, site_zone
from energy_lab.core.units import EnergyKWh, average_power_from_energy, finite_number, parse_energy, parse_power
from energy_lab.data.manifest import canonical_sha256
from energy_lab.simulation.observer import ObservedRecord


POWER_SIGNALS = frozenset({
    "metered_building_load_kw",
    "pv_available_kw", "pv_used_kw", "critical_load_kw", "fixed_load_kw",
    "flexible_load_kw", "grid_import_kw", "grid_export_kw",
    "battery_charge_kw", "battery_discharge_kw", "ev_power_kw",
    "pump_power_kw", "hvac_power_kw",
})
ENERGY_STATE_SIGNALS = frozenset({"battery_soc_kwh"})
TEMPERATURE_SIGNALS = frozenset({"outdoor_temperature_c", "indoor_temperature_c"})
REQUIRED_COLUMNS = frozenset({"start", "end", "quantity", "value", "unit"})


class DataIngestionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImportedDataset:
    dataset_id: str
    site_timezone: str
    records: tuple[ObservedRecord, ...]
    source_sha256: str
    normalized_sha256: str


def _parse_timestamp(raw: str, zone_name: str, fold_raw: str | None) -> datetime:
    parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc)
    fold = None if fold_raw in (None, "") else int(fold_raw)
    return local_to_utc(parsed, zone_name, fold=fold)


def _convert_value(quantity: str, value: float, unit: str, interval: TimeInterval) -> tuple[float, str]:
    if quantity in POWER_SIGNALS:
        if unit in {"W", "kW", "MW"}:
            return parse_power(value, unit).value, "kW"
        if unit in {"Wh", "kWh", "MWh"}:
            energy = parse_energy(value, unit)
            return average_power_from_energy(EnergyKWh(energy.value), interval.duration).value, "kW"
        raise ValueError("power signal requires W/kW/MW or interval Wh/kWh/MWh")
    if quantity in ENERGY_STATE_SIGNALS:
        return parse_energy(value, unit).value, "kWh"
    if quantity in TEMPERATURE_SIGNALS:
        if unit not in {"°C", "C"}:
            raise ValueError("temperature signal requires °C")
        return value, "°C"
    raise ValueError(f"unsupported quantity: {quantity}")


def ingest_csv_text(text: str, *, dataset_id: str, site_timezone: str) -> ImportedDataset:
    if not dataset_id:
        raise DataIngestionError("dataset_id is required")
    site_zone(site_timezone)
    source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
        raise DataIngestionError(f"CSV requires columns: {', '.join(sorted(REQUIRED_COLUMNS))}")
    records: list[ObservedRecord] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            start = _parse_timestamp(row["start"], site_timezone, row.get("start_fold"))
            end = _parse_timestamp(row["end"], site_timezone, row.get("end_fold"))
            interval = TimeInterval(start, end)
            quantity = row["quantity"].strip()
            value = finite_number(float(row["value"]), "CSV value")
            normalized_value, normalized_unit = _convert_value(quantity, value, row["unit"].strip(), interval)
            records.append(ObservedRecord(interval, quantity, normalized_value, normalized_unit))
        except (KeyError, TypeError, ValueError) as exc:
            raise DataIngestionError(f"CSV line {line_number}: {exc}") from exc
    if not records:
        raise DataIngestionError("CSV contains no data rows")
    normalized = tuple(sorted(records, key=lambda r: (r.quantity, r.interval.start, r.interval.end)))
    return ImportedDataset(dataset_id, site_timezone, normalized, source_hash, canonical_sha256(normalized))
