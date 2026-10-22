# Flexibility model and units

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) fixes all signs, interval conventions, disjoint load categories, terminal SOC and baseline details. This document supplies the conceptual derivation.

Time index `t=0..T−1`, duration `Δt` hours (0.25, 0.5, or 1). Power is kW, energy kWh, money INR. All series use one site timezone and UTC storage. Positive site power means **grid import**. Baseline means a fixed, reproducible no-new-action schedule under the same weather/demand realization; it is not automatically the historical meter trace.

## Definitions

Let `L^0_t` be baseline gross electric load, `L^obs_t` actual gross load if separately metered, `G^0_t` baseline PV generation, `b^0_t` baseline battery discharge minus charge, and `P^0_t=L^0_t−G^0_t−b^0_t` baseline net grid power (positive import, negative export), subject to connection limits. Actual observed net meter power is `P^obs_t`; deviation `P^obs_t−P^0_t` is not causal flexibility without controls and a valid counterfactual. A site meter alone does not identify `L^obs_t`, PV output and battery dispatch separately.

For a candidate feasible schedule `s`, `P_t(s)` is net grid power. **Downward grid flexibility** at `t` is `F↓_t=max_s [P^0_t−P_t(s)]_+`; **upward grid flexibility** is `F↑_t=max_s [P_t(s)−P^0_t]_+`. These are separate maximizations and generally cannot be delivered simultaneously. Gross flexible load is an asset's admissible power range and deferrable energy, not the sum of nameplate ratings. For requested direction `d`, sustained power `q` over window `W` is feasible only if there exists one schedule satisfying `P_t(s)≤P^0_t−q` (downward) or `P_t(s)≥P^0_t+q` (upward) for every `t∈W`, plus all service and recovery constraints. The duration is `|W|Δt`; delivered energy is `q|W|Δt`, not `q` alone. An asset's earliest activation, latest finish, response delay, ramp `|p_t−p_{t−1}|≤RΔt`, and required recovery period define its availability window and response/recovery times.

**Theoretical** envelope uses ratings and windows only. **Technically feasible** adds physical limits, energy balance, SOC, ramp, and connection limits. **Operationally feasible** adds comfort, required service, critical load, user permissions, and tariff-independent schedules. **Reliable** flexibility `q_α(W)` is the largest `q` whose required service is feasible in at least `1−α` of explicitly sampled/held-out uncertainty realizations, with the method and sample size displayed; this is a scenario reliability estimate, not a safety guarantee. If data are too poor to calibrate uncertainty, output `unknown`, not 90% confidence.

## Asset and system equations

| Quantity | Definition / calculation |
|---|---|
| Battery SOC `E_t` (kWh) | `E_{t+1}=E_t+η_c c_t Δt−d_t Δt/η_d`; `E_min≤E_t≤E_max`; `0≤c_t≤C_max`; `0≤d_t≤D_max`; `0<η_c,η_d≤1`. SOC%=`100E_t/E_capacity`. |
| Battery power/energy | Charge/discharge rating `C_max,D_max` in kW; usable energy `E_max−E_min` in kWh. No simultaneous charge and discharge in a final feasible schedule. |
| Flexible EV | `0≤p_EV,t≤P_EV,max a_t`; `Σ_{t in window}p_EV,t Δt≥E_required`; charging efficiency converts wall energy to delivered EV energy when modeled. Departures constrain finish. |
| Pump | On/off or bounded `p_pump,t`; water/service requirement `Σ p_pump,t Δt≥E_pump,required` only when electric energy is an appropriate proxy. Tank volume and flow constraints supersede proxy where known. |
| HVAC | `p_HVAC,t` within equipment limits and thermal state `θ_{t+1}=aθ_t+bθ_out,t−c p_HVAC,t Δt`, with comfort range during occupied periods. If coefficients are unknown, use conservative window bounds and label them assumed. |
| Critical load | `L_crit,t` served in every admissible schedule; unmet critical service must be zero or the run is invalid. Non-flexible load is fixed for a scenario. |
| PV curtailment | `0≤u_t≤G_avail,t`; PV used `G_avail,t−u_t`; curtailment energy `Σu_tΔt`. Renewable utilization=`1−Σu_tΔt/ΣG_avail,tΔt` if denominator positive; otherwise N/A. |
| Grid power | Import `i_t≥0`, export `e_t≥0`, `P_t=i_t−e_t`; enforce connection ratings, and no simultaneous import/export in final schedules. |
| Power balance | `G_avail,t−u_t+i_t+d_t = L_fixed,t+Σ_a p_a,t+c_t+e_t`. Residual must be near zero at every interval. |
| Peak demand | `max_t i_t` kW over a declared horizon; tariff billing peak may have a different measurement rule. |
| Unmet service | Positive shortfall in required EV energy, pumping service, or comfort degree-hours; each reported separately. Critical load shortfall is prohibited. |

**Energy flexibility** must specify a window and direction: `Σ_t(P^0_t−P_t(s))Δt` for downward grid response, or reverse for upward. It can include rebound outside the window, so report recovery energy and net daily import too. The aggregate envelope requires joint optimization; summing independent asset maxima double counts shared connection, PV, SOC, and time constraints.

No composite flexibility score in MVP. kW-by-time, duration, deliverability, and uncertainty are more interpretable. A future score needs a documented use decision and external validation against actual response events.
