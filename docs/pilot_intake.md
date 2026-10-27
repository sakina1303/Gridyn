# Advisory pilot intake (operator worksheet)

**Status: template only.** No facility has supplied consented data or approved operating constraints. This study runs in shadow mode; FlexGrid does not control equipment.

## Decision to test

For a specified 1, 2, or 4 hour window, can the site reduce or increase grid import while keeping critical loads, asset service and operator limits intact? Record the response in kW, recovery energy in kWh, failures, abstentions and uncertainty. Do not state savings or reliability until measured and independently reviewed.

## Facility and permission

| Field | Operator entry |
|---|---|
| Facility type and site timezone | Pending |
| Named facility contact | Pending |
| Permission to use records for this research | Pending |
| Approved users, retention period and storage location | Pending |
| Prohibited actions and critical services | Pending |

Keep private records outside the public repository. The local prototype has no multi-user access control; agree on secure storage before importing private data.

## Records to request

For each series, record source, timestamp convention, unit, meter sign, resolution, date range, gaps and owner. Request 15-minute grid import/export readings first. Add PV output and curtailment, battery SOC and AC power, EV arrival/departure and delivered energy, pump runtime/service, and indoor temperature/comfort only for assets present. Record actual equipment ratings, availability and operator-approved windows. A tariff order is needed only for a cost claim; do not assume a rate.

| Record | Present? | Source and period | Quality issue | Collection effort / cost estimate |
|---|---|---|---|---|
| Site import/export | Unknown | Pending | Unknown | Operator estimate needed |
| PV and curtailment (if installed) | Unknown | Pending | Unknown | Operator estimate needed |
| Battery SOC and AC power (if installed) | Unknown | Pending | Unknown | Operator estimate needed |
| EV service logs (if applicable) | Unknown | Pending | Unknown | Operator estimate needed |
| Pump service logs (if applicable) | Unknown | Pending | Unknown | Operator estimate needed |
| Indoor comfort (if HVAC is assessed) | Unknown | Pending | Unknown | Operator estimate needed |

## Evaluation and sign-off

Freeze chronological training, calibration and test periods before scoring. Run the advisory recommendation without applying it to equipment. Compare it with observed outcomes and record every infeasible, failed and abstained case. Ask the operator to review constraints and any service or comfort violation. Record code revision, data hashes, forecast issue times, solver version and corrections. Use the full [validation gate](pilot_validation.md) before making a field claim.

**Current measured savings, field reliability, grid benefit and operator acceptance: Unknown.**
