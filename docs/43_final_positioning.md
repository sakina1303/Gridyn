# Positioning copy (provisional; product name pending)

**One sentence:** A research prototype that tests how much flexibility a small energy site can reliably offer when its data are incomplete.

**30 seconds:** Campuses with solar, batteries, cooling, EVs and pumps have options to shift electricity use, but a nameplate kW total does not tell an operator what can safely move at a particular time. This advisory tool checks the data, estimates feasible response under service constraints, tests uncertainty, and explains what to measure next. Its first results are simulations, not field performance.

**One minute:** The tool begins with a site data audit: what is metered, inferred, and missing. It then models each asset's operating window and energy obligation, forecasts demand and PV with simple baselines, and computes feasible upward or downward grid response for a stated duration. A formal scheduler compares actions with no-action and simple-rule baselines. Stress scenarios test whether the response survives imperfect forecasts and behavior. The output is an auditable recommendation and research report. A campus is the first testbed; the method could later apply to similar small sites, contingent on real-data validation.

**Technical abstract:** We propose a simulation-first workflow for data-readiness assessment, constraint-based site flexibility envelopes, and scenario-tested reliability under incomplete time-series and asset observations. Paired synthetic campus experiments ablate resolution, history, missingness, and asset-meter coverage; compare conservative rules with mathematical scheduling; and measure overstatement, service violations, decision regret and the marginal value of additional measurements. External validity requires a later consented-data shadow study.

**Research abstract:** This project asks how little information is sufficient to make a useful, calibrated flexibility promise at a small distributed energy site. Rather than treating dispatch optimization as novel, it studies the relationship between data quality, feasible response, and confidence. It will report where the model abstains as well as where it succeeds.

**IRENA application explanation:** Distributed flexibility can help align demand and storage with variable renewable generation. Our contribution is a transparent way to examine its availability and reliability at the site level, complementing broader grid planning. The prototype will use reproducible campus simulations and openly state limitations. [IRENA FlexTool context](https://www.irena.org/Energy-Transition/Planning/Flextool)

**GitHub README opening:** Working-name project: an advisory, simulation-first flexibility readiness and decision lab for Indian campuses and similar sites. It quantifies feasible response and exposes uncertainty, missing data, assumptions, and baseline comparisons. It is not a grid controller or a validated commercial EMS.

**Portfolio description:** Designed a research prototype for site energy flexibility assessment under sparse data, combining physical constraints, forecast evaluation, scenario testing and explainable recommendations.

**Resume bullets (use only after implementation):** “Built a constraint-validated campus energy simulator and optimization workflow for solar, storage and flexible loads.” “Designed ablation experiments linking data resolution and missingness to flexibility overstatement and decision reliability.” Add quantified results only after measured experiments.
