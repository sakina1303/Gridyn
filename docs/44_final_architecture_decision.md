# Architecture decision — conditional design approval

## Decision

Build an **advisory, simulation-first flexibility readiness and decision lab** for a campus archetype, then test transfer to similar small sites. The temporary label is FlexGrid; the product name remains open. Primary user: facility/energy manager. Core research contribution candidate: a calibrated, useful response envelope under incomplete site data and a method for identifying the most valuable next measurement.

The MVP contains a synthetic physical model, typed data import/readiness, baseline and simple forecasts, feasibility envelope, small MILP scheduler, uncertainty stress tests, paired scenario comparison, structured explanation and reproducible report. It excludes control, power-flow/voltage claims, market participation, live utility integration, complex auth, and unsupported carbon or savings claims. See [scope](33_mvp_scope.md).

## Evidence and assumptions

The India need is supported by [CEEW's DISCOM research](https://www.ceew.in/publications/how-india-can-create-demand-flexibility-market-five-pillars). Existing scheduling and flexibility tools mean the novelty claim is **not** optimization itself; [FlexMeasures](https://flexmeasures.io/) is a direct reference. Our exact unmet product gap is still unverified. No operator interviews, partner data, dataset audit, or comprehensive literature novelty review have yet been completed. Therefore this document locks only a **research prototype design hypothesis**, not a commercial product claim or field deployment architecture.

## Data and proof

Needed first: deterministic synthetic truth/observation pairs, asset ratings/windows/obligations, versioned tariff scenarios, weather and local timestamps. Later: consented 15 minute site/PV/asset data, SOC and schedules, verified tariff. Experiments [31](31_experimental_protocol.md) test baseline versus optimization, imperfect forecasts, missingness, resolution, asset sizes/mix, tariffs, and uncertainty. Success requires physical correctness, useful but calibrated/qualified response, fewer over-promises than conservative rules, and operator-relevant output. It is invalidated if an existing tool already solves the same low-data assessment with similar burden, if uncertainty bounds are unhelpfully wide, if overstatement persists, or if no data path exists for eventual validation.

## Build order and gates

First build a unit-tested physical simulator and baseline. Next implement readiness and full-information flexibility, then ablations and uncertainty, then optimizer and forecast comparisons, then API/UI/report. [Canonical model](46_canonical_model.md), [design review](45_design_review.md), and [implementation plan](58_implementation_plan.md) fix conventions and dependencies. Before a real pilot, separately complete consent, security, meter reconciliation and shadow-mode review.
