# Product definition (design hypothesis)

**Name:** FlexGrid is a temporary working label. **One sentence:** An advisory research tool that estimates feasible and reliable energy flexibility for small distributed sites with incomplete data, then tests transparent actions against a baseline.

## Final challenge to the direction

| Question | Answer |
|---|---|
| Exact problem | Operators may know total consumption yet lack asset-level visibility, trustworthy flexible kW by time and duration, and evidence that a suggested shift will preserve service. |
| Who | First: campus facility/energy manager. Later: hostels, municipal facilities, small C&I sites; secondary: researchers, consultants, DISCOM planners. |
| Why India | CEEW reports limited granular local flexibility analytics and data barriers in its DISCOM survey; rooftop solar and time-of-day signals increase the value of timing decisions. [CEEW](https://www.ceew.in/publications/how-india-can-create-demand-flexibility-market-five-pillars) |
| Grid/storage connection | Load shifts and storage change site import/export and possible connection peaks; site results do not establish feeder voltage or stability benefits. |
| Existing tools | FlexMeasures already schedules and forecasts assets; IRENA FlexTool plans at system scale. The possible gap is a low-data, uncertainty-aware **assessment and evidence workflow**, not an unserved optimizer. [FlexMeasures](https://flexmeasures.io/), [IRENA](https://www.irena.org/Energy-Transition/Planning/Flextool) |
| Differentiation | Report feasible and reliable envelopes, assumptions, data sufficiency, failure cases, and the marginal value of another measurement before recommending action. This is a hypothesis, not proven novelty. |
| Research-worthy | Minimum data thresholds, uncertainty calibration, reliability under imperfect forecasts, and measurement value across asset mixes. |
| Normal engineering | CRUD, charts, authentication, exports, API wiring, dashboard styling. |
| Unverified assumptions | Operators want this report, can supply operating constraints, accept advisory recommendations, and permit a later shadow pilot. |
| Failure conditions | Existing tools solve this comparably; insufficient data makes bounds too wide; unsafe recommendations; no partner data; no material gain over rules; results cannot generalize. |

The direction remains the strongest **research hypothesis** from [15–20](19_recommended_product_direction.md), but the competitive review was a screening exercise. Do not call the gap proven.

## User and journey

Primary user: campus facilities manager. Secondary users: energy researcher, sustainability office, consulting engineer, and later a DISCOM planning analyst. Journey: define site and operating objectives → upload or select simulated data → inspect readiness and missing inputs → see baseline and flexibility envelope → run forecast/optimization/scenarios → review confidence and service tradeoffs → export an evidence report → collect better data.

## Jobs, inputs, outputs

| Jobs | Inputs | Outputs |
|---|---|---|
| Know what can shift, when, for how long, and how reliably | Timestamped import, optional PV/asset meters; asset ratings/windows/requirements; weather; tariff; site limit | Readiness verdict, baseline, per-asset and aggregate feasible envelopes, reliability estimate, assumptions |
| Compare candidate actions and investments | Forecasts, uncertainty scenarios, battery and load settings | Dispatch schedule, peak/cost/curtailment/service metrics against same baseline |
| Decide what to measure next | Missingness and parameter sensitivity | Ranked measurements with estimated effect on decision uncertainty |

## Use and non-use

Core workflows: data assessment, flexibility estimation, scenario comparison, structured recommendation, research report. Main use cases: solar surplus shifting, evening import peak reduction, battery sizing sensitivity, missing-data audit. Non-use cases: autonomous dispatch, utility settlement, protection studies, AC power flow, verified carbon accounting without factors, direct control, market bidding.

**MVP:** one simulated site, CSV ingestion, readiness, bounded flexibility, simple forecasts, deterministic scenarios, formal scheduling, baseline comparisons, explainable results. **Post-MVP:** real historical data, calibrated reliability, multi-site comparison, tariff library, feeder constraints with utility data. **Research prototype:** reproducible methods and honest uncertainty. **Future commercial product:** audited integrations, access control, cybersecurity, live operations, support, and regulatory review; none are claimed now.
