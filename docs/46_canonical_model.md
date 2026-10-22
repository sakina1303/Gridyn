# Canonical physical and temporal model

This document is authoritative for simulation, data normalization, forecasting, envelopes, optimization, metrics, API and UI. Other documents describe features and must not redefine these conventions.

## Time, units and signs

Intervals `t=0,…,T−1` are half-open `[τ_t,τ_t+Δ)` in UTC; `Δ∈{0.25,0.5,1}` hours. The synthetic truth grid is `Δ=0.25`; coarser observed datasets are derived by energy-preserving aggregation. Site IANA timezone governs displayed local time and tariff schedule. Internal power is average kW during an interval, energy is kWh, temperature °C, money INR. An interval energy meter value `x_t` kWh becomes average power `x_t/Δ` kW. Never sum kW as though it were kWh.

All gross physical flows are nonnegative: available PV `g_t`, curtailment `u_t`, grid import `i_t`, grid export `e_t`, battery AC charge `c_t`, battery AC discharge `d_t`, critical load `Lcrit_t`, noncritical inflexible load `Lfixed_t`, and each flexible load `l_{a,t}`. Net grid power `P_t=i_t−e_t`; positive means importing. Upward *grid* flexibility increases `P`, downward decreases `P`. Demand never has a negative sign; generation is a supply term.

## Balance and bounds

`g_t−u_t+i_t+d_t = Lcrit_t+Lfixed_t+Σ_a l_{a,t}+c_t+e_t`, with `0≤u_t≤g_t`, `0≤i_t≤Imax`, `0≤e_t≤Xmax`; import and export cannot both be positive in a final schedule. `Lcrit_t` is always served; `Lfixed_t` excludes critical and all modeled flexible load. If HVAC has uncontrollable and controllable portions, place them in `Lfixed` and `l_HVAC` respectively, never both. Curtailment is physical PV available but unused. PV used is `g_t−u_t`.

Battery energy `E_t` is kWh at interval start. `E_{t+1}=E_t+ηc c_tΔ−d_tΔ/ηd` with `0<ηc,ηd≤1`, `Emin≤E_t≤Emax`, `0≤c_t≤Cmax`, `0≤d_t≤Dmax`, no simultaneous `c,d`. Rates are AC-bus kW. SOC fraction is `E_t/E_nominal`, display `%` only after ×100. Configured nominal capacity, SOC min/max fractions, initial energy, rate limits and efficiencies are distinct fields. Paired comparisons use identical initial SOC and terminal `E_T≥E_0` unless a documented longer carryover run replaces this guard. No battery case sets `c=d=0` and omits `E`.

Each asset has an availability indicator `a_{a,t}`, power bound `0≤l_{a,t}≤Pmax_a a_{a,t}`, optional minimum stable power and ramp `|l_{a,t}−l_{a,t−1}|≤R_aΔ` where justified. EV energy delivered by departure must meet session demand after charger efficiency. Pump must meet a declared volume, runtime or energy proxy; the proxy cannot be labeled water-service proof. HVAC comfort is either a calibrated thermal state constraint or a conservative operator-approved window and bound. Minimum runtime/start constraints use binary decisions only when the equipment requires them. Response delay, recovery and rebound obligations remain within an explicit evaluation horizon. Unknown parameters produce bounded scenarios or abstention, never a secretly assumed firm rating.

## Baseline, flexibility and reliability

Baseline `P^0_t` is the valid no-new-action schedule under the **same hidden truth**, with required EV/pump/HVAC service fulfilled and battery idle; it is saved and versioned. Metered `P^obs` is an observation, not the counterfactual. For a window `W=[s,s+D)`, a downward response of `q≥0` kW requires one jointly feasible schedule with `P_t≤P^0_t−q` for all `t∈W`; upward response requires `P_t≥P^0_t+q`. Recovery/terminal constraints apply through the evaluation horizon. Per-time maximum envelopes may be displayed but cannot be summed over time or assets. Response energy is `qDΔ` kWh for D intervals; actual shifted energy and rebound are separately integrated. Theoretical, technical, operational and scenario-tested reliable levels follow [22](22_flexibility_model.md). A “reliable” number always names target success fraction, scenario source, test count and calibration status. Otherwise value is `unknown`.

## Derived metrics

Grid import/export energy `Σ i_tΔ`, `Σe_tΔ`; PV curtailment `Σu_tΔ`; PV utilization `(Σ(g_t−u_t)Δ)/(Σg_tΔ)` when denominator >0; peak study import `max_t i_t`; battery discharge throughput `Σd_tΔ`; equivalent full cycles = discharge throughput / usable kWh (`Emax−Emin`) when capacity >0. Cost is only computed against a versioned or explicitly synthetic tariff formula including relevant demand and export terms. All metrics carry horizon, resolution, baseline, truth/observed label and units. Hard-constraint residuals must be recomputed independently after every solve.
