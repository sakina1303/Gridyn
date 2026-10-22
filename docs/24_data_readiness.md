# Data readiness contract

**Implementation authority:** [49_data_readiness_implementation.md](49_data_readiness_implementation.md) defines the API verdicts `usable`, `usable_with_limitations`, `insufficient`, and `invalid`. The levels below describe the strength of the *evidence for a claim* and map to those verdicts as stated in 49.

Readiness is **claim specific**, not one global percentage. Levels: `blocked` (cannot form valid estimate), `bounded` (assumption-based interval), `retrospective` (historical validation possible), `prospective` (calibrated shadow evaluation possible). No level authorizes physical control.

| Input | Required minimum for modeled claim | Recommended / optional | Time/resolution and units | Main checks / fallback |
|---|---|---|---|---|
| Site grid import/export | Required for site baseline and peak | ≥30 representative days, preferably seasons | 15–60 min, kW or kWh/interval; sign explicit | Gaps, duplicate times, negative values, meter resets; if absent, simulation only |
| PV capacity and output | Capacity required for PV scenario; meter needed for measured utilization | ≥30 days PV output plus weather | 15–60 min kW/kWh; capacity kWp/kW AC explicit | Night generation, above plausible rating, clipping; estimated PV must be labeled inferred |
| Battery | Rating, usable kWh, SOC bound, charge/discharge rates, efficiency required for safe schedule | Metered SOC and power at each step; degradation data optional | kW, kWh, %; initial SOC timestamp | SOC continuity and limits; missing SOC → bounded scenario, no firm discharge claim |
| EVs | Charger kW, availability, energy due and departure required | Session history ≥30 days | Per session time and kWh | Impossible energy/window, overlaps; unknown arrivals → scenarios |
| HVAC | Equipment kW and permission/comfort bounds required | Temperature, occupancy, thermal response ≥30 days | kW, °C, timestamp | Comfort range and sensor drift; no thermal data → conservative fixed window only |
| Pumps | Power and permitted window/service requirement required | Flow/tank state and history ≥30 days | kW, volume or hours | Service feasibility; no tank model → no water-system claims |
| Tariff | Required only for cost claims | Current applicable state/category order and bill rules | INR/kWh, INR/kW, local effective dates | Version and category check; absent → physical metrics only |
| Weather | Required for weather-driven forecast; optional for deterministic profile | ≥30 days aligned observations or documented external source | °C, irradiance W/m², cloud proxy | Timestamp alignment and missingness; no source → scenario only |
| Schedules/critical loads | Required for operational feasibility | Operator confirmation and overrides | Local time windows, kW | Conflicts, holidays, non-flexible labels |

**History is task dependent:** zero history supports only declared synthetic or engineering bounds; 30 days permits a weak retrospective within that period but not seasonal generalization; six months may cover one season transition; a year permits first seasonal evaluation. These are design gates to test, not validated minimums. Fifteen minute data captures short peaks that hourly averages can hide; hourly data may support coarse energy shifting but cannot prove 15 minute peak response.

Normalize timestamps to UTC with IANA site timezone retained; record interval start/end, daylight-saving ambiguity, and source clock. India sites normally use `Asia/Kolkata`, but schema must not hardcode it. Convert interval kWh to average kW by dividing by `Δt` hours. Never fill long gaps silently. Short gaps may be imputed for forecasting with method/flags; metric denominators and reliability tests must exclude or explicitly account for imputed intervals. Outliers are flagged for review, not discarded merely for being inconvenient. Every field stores provenance (`metered`, `operator`, `inferred`, `synthetic`), quality flags, and parameter range.

Example verdicts: “Enough data for a **simulation-bound** battery response; no timestamped SOC, so firm battery flexibility is unknown.” “Hourly site data can support daily cost scenarios but not a measured 15 minute peak claim.” “Collect 15 minute PV output and battery SOC for four representative weeks to narrow the tested range; seasonal confidence still requires more data.”
