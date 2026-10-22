# Failure modes and safe behavior

| Failure | Detection | Product behavior |
|---|---|---|
| Missing, duplicate, shifted, or noisy meter intervals | Quality checks, source reconciliation | Flag affected times; downgrade claim, abstain if baseline invalid |
| PV/forecast error or unexpected weather | Held-out error, drift, stress replay | Widen range or no firm response; rerun scenarios |
| Battery unavailable or SOC unknown | Stale/missing telemetry or impossible SOC | Remove battery from firm envelope; use bounded sensitivity only |
| EV arrivals/departures change | Session updates and missed service | Protect departure energy; withdraw infeasible recommendation |
| Tariff changes or wrong category | Source/effective date mismatch | Suppress cost claim until verified; physical result may remain |
| Infeasible optimization/time limit | Solver status and independent validation | Show status and conflicting constraints; no dispatch advice |
| Conflicting objectives | Cost/peak/curtailment tradeoff report | Show objective profile and worsened metrics |
| Excessive shifting/rebound | Recovery horizon and service audit | Report rebound and cap response duration |
| Comfort, pump, or critical load breach | Constraint residuals and operator feedback | Critical breach invalidates run; service deficit diagnostic only |
| False confidence or calibration drift | Reliability by period/season; coverage test | Label unknown or downgrade; request new data |
| Synthetic-to-real mismatch | Pilot reconciliation | No transfer of simulated savings claims |

Every calculation carries `status`, assumptions, data provenance, and limitations. The interface explicitly says “insufficient evidence” where appropriate. Human operator makes all real asset decisions.
