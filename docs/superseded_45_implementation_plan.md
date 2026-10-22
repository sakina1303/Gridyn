# Dependency-ordered implementation plan (no code yet)

| Stage | Deliverable | Depends on | Exit gate |
|---|---|---|---|
| 0 | Review evidence, interview plan, one state/tariff example, dataset license audit | Research 15–20 | Gap and data access assumptions recorded; architecture remains conditional |
| 1 | Units, time-index convention, typed assets and immutable run config | 22, 24, 35 | Unit/time tests; no silent conversions |
| 2 | Synthetic truth and observation generator; fixed baseline and rule | 1, 26 | Balance/service/SOC properties pass; seed reproduces dataset |
| 3 | Data import, quality checks and claim-specific readiness | 1–2, 24 | Missing/noisy/timezone fixtures yield expected verdicts |
| 4 | Full-information feasible up/down envelopes | 2–3, 22 | Sustained-response joint feasibility and rebound tests |
| 5 | Persistence/linear forecast, rolling evaluation and simple stress scenarios | 2–4, 23, 28 | No leakage; intervals labeled calibrated or unknown |
| 6 | LP debug model then small MILP schedule; independent validation | 2–5, 27 | Feasible status, zero hard residuals, baseline comparison |
| 7 | Minimum-data ablations and ten registered experiments | 3–6, 25, 31 | Reproducible overstatement/regret/service results, including negatives |
| 8 | Structured recommendations, report, API | 3–7, 29, 36 | Every number traceable to run and baseline |
| 9 | Focused UI: setup, readiness, assessment, scenario, report | 8, 37 | Operator can distinguish synthetic, observed, uncertain, infeasible |
| 10 | End-to-end demo and independent review | 1–9, 38, 42 | Seven-minute story reproducible; limitations prominent |
| 11 | Optional real-data shadow pilot | Partner consent and 10 | Historical/shadow errors measured; no control |

Avoid an all-at-once frontend build. At every stage freeze a small reproducible fixture and stop optional features when the exit gate passes. Revisit architecture after stage 0 if the gap or partner data path fails. Implementation begins only on a later explicit instruction.
