# Campus simulation specification

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) and [47_simulator_spec.md](47_simulator_spec.md). A one-week demo consists of comparable 24-hour scheduling runs; 15-minute ground truth can be aggregated into coarser observations.

All numeric values below are **configurable synthetic assumptions**, not measurements of an Indian campus. One week at 15 minute resolution is the first demo; multiple seasonal weeks test robustness. Choose a documented local timezone, weather regime, weekday/weekend calendar, and random seed. Archive every generated input and generator version.

| Component | Initial illustrative setting | Physical/operational rule |
|---|---|---|
| PV | 100 kW AC maximum | Zero at night, irradiance/cloud/temperature variation, optional curtailment |
| Grid | 250 kW import, configurable export cap | Import/export mutually exclusive; outages only in explicit scenarios |
| Battery | 200 kWh nominal, 50 kW each direction, SOC 20–90%, `ηc=ηd=0.95` | SOC dynamics and reserve enforced |
| Fixed/critical load | Peak gross site demand roughly 150–250 kW | Critical portion never shed; occupancy/calendar variation |
| Cooling | Up to 60 kW controllable subset | Occupied comfort band or conservative shift window |
| EV charging | 40 kW aggregate | Arrival/departure/required kWh per session |
| Pumps | 20 kW | Required volume or runtime in allowed window; service never silently skipped |
| Weather/tariff | Synthetic weather; versioned tariff scenario | Label assumptions; no claim of actual state bill savings |

At each interval generate weather → available PV and uncontrollable demand → asset obligations/windows → baseline schedule → observations with optional noise/missingness. Validate energy balance and feasible service. Separate **truth** (used to score outcomes) from **observed data** (shown to planner); otherwise missing-data tests leak the answer.

Scenario A: no flexible action; B: transparent rule (solar-first EV/pump, fixed reserve); C: deterministic optimization; D: stress-safe optimization under forecast error; E: limited observed data; F: high-quality observed data. All scenarios share the same hidden weather, demand, asset obligations, tariff, and initial SOC when compared. Report cost under stated tariff, import peak, grid energy, PV used/curtailed, battery throughput, service deficits, feasible/reliable response, and solver status. A scenario may be infeasible; display why.
