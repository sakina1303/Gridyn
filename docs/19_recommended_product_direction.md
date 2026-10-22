# Recommended direction — provisional

**Working name:** FlexGrid. Decide the project name after the product direction has been tested.

## Recommendation

Build a **flexibility readiness and decision lab for Indian campuses and similar small sites**. Its central question is: *given the data and assets this site actually has, what flexibility can be delivered safely, when, with what confidence, and what measurement would most improve the decision?*

The first demonstration should simulate solar, a battery, cooling, EV charging, and pumping, with configurable operational limits. It should compare no action, simple operating rules, and formal optimization. The distinctive research layer should report feasibility bounds, sensitivity to forecast and tariff assumptions, and data quality or missing data requirements. An explainable recommendation must cite the modeled constraints and baseline effect.

## Why this direction

- **India:** DISCOM research identifies limited local flexibility analytics and granular data barriers. India also has active solar, storage, smart metering, and time of day policy development. [CEEW market study](https://www.ceew.in/publications/how-india-can-create-demand-flexibility-market-five-pillars), [MNRE rooftop programme](https://mnre.gov.in/en/grid-connected-solar-rooftop-programme/)
- **Grids, storage, flexibility:** the assessment quantifies which load or storage response is available during a local peak or solar surplus period, subject to site limits. Connection limit scenarios are valid; claims about feeder voltage or stability await network data.
- **Buildability:** the demonstration can use deterministic simulation, a formal optimization model, and explicit uncertainty scenarios. No hardware is necessary for the research prototype.
- **Quantitative testing:** measure power balance, feasible kW/kWh, baseline versus optimized cost under specified tariffs, peak import, curtailment, unmet service, and robustness across scenarios. Report failures and infeasible cases.
- **Pilot path:** obtain consented interval meter data, asset ratings, operating windows, and applicable tariff from one campus. Shadow run the recommendations before any control integration. Compare predicted and measured outcomes.
- **Scalability:** the same site and asset schema can cover hostels, municipal facilities, and small commercial buildings. Network aggregation is a later research stage.
- **IRENA relevance:** it makes flexibility visible and testable at the distributed edge, complementing system scale planning such as IRENA FlexTool. [IRENA FlexTool](https://www.irena.org/Energy-Transition/Planning/Flextool)

## Claims to avoid

Do not say it is the first optimizer, first campus EMS, first pump shifting project, or first Indian VPP. Existing examples contradict those claims. [FlexMeasures](https://flexmeasures.io/), [Tata Power pumping pilot](https://www.tatapower.com/news-and-media/media-releases/tata-power-joins-hands-with-mcgm-for-a-unique-demand-flexibility-program-powered-by-solar-energy), [Amperehour VPP](https://amperehourenergy.com/bses-rajdhani-indias-first-multi-site-virtual-power-plant-vpp/)

## Decision gates before architecture lock

1. Validate the user problem with at least three campus or facility operators and one distribution planning expert.
2. Audit accessible datasets and licensing; identify which metrics can be evaluated on real data.
3. Select a state and tariff category; record tariff order version and applicability.
4. Reproduce an existing open source optimizer example to establish the true difference.
5. Write a one page experimental protocol with uncertainty and baseline definitions.

Until these gates are complete, this is a **provisional product direction**, not a locked MVP architecture.
