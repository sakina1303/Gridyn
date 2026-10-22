# Numerical validation cases before UI

All cases use [46](46_canonical_model.md), two or four 1 h intervals where possible, hand-calculated expected values and independent balance/SOC checks. The test file will state exact inputs/results; below are the required oracle behaviors.

| Case | Expected invariant / analytical result |
|---|---|
| No battery | `c=d=0`; with PV=0, import equals total demand when export=0 |
| No solar | `g=u=0`; no fabricated renewable utilization percentage |
| Unlimited flexible *capacity* | Still bounded by service energy, operating window, grid limit and recovery; no infinite envelope |
| Zero flexible load | Only battery/PV/grid capability remains; no fictitious demand response |
| Battery at max SOC | `c=0` initially unless headroom created by discharge; discharge ≤rating/energy |
| Battery at min SOC | `d=0` initially unless first charged; SOC never below min |
| No grid import | Model feasible only if PV/storage can serve all critical/fixed/required demand; otherwise infeasible, never shed critical |
| No curtailment | With PV surplus, export/storage/flexible demand must absorb it or model is infeasible |
| No flexibility | Sustained up/down `q=0` if all actions fixed and no storage/headroom |
| Single EV asset | If 20 kWh due over two 1 h slots at 20 kW, valid schedules include 20+0 or 0+20 only within availability; response window constrained by service |
| Multiple interacting assets | Joint envelope ≤ relevant shared grid/energy limit even if independent asset maxima sum higher |
| Battery efficiency | 10 kW charge for 1 h at `ηc=.9` adds 9 kWh; 9 kWh delivered at `ηd=.9` consumes 10 kWh stored |
| PV curtailment | `g=100`, total load=40, charge cap=20, export cap=0, extra flexible load=10 → at least 30 kW curtailed in that interval, given all those loads available |
| Terminal SOC | Battery cannot lower total billed import by draining its initial energy while ending below required terminal reserve |

Numerical checker validates all intervals, not sampled points. For each case test both direct simulator replay and optimization output when applicable. Infeasible cases assert structured status and no recommendation.
