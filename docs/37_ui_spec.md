# UI specification

**Implementation authority:** use [46_canonical_model.md](46_canonical_model.md) for signs/units, [49_data_readiness_implementation.md](49_data_readiness_implementation.md) for verdict names, and [50_response_envelope.md](50_response_envelope.md) for sustained-response terminology.

The primary path is **Site Setup → Data Readiness → Flexibility Assessment → Scenario Lab → Recommendation → Research Report**. Ten named areas can initially be tabs/sections rather than ten fully separate pages.

| Screen | User question and essential display |
|---|---|
| Site Setup | What site/assets/constraints are modeled? Input provenance, units, local time and synthetic badge. |
| Data Readiness | Which claims are supported? Claim-specific `blocked/bounded/retrospective/prospective`, gaps, quality timeline, next measurement. |
| Energy Overview | How do PV, demand, import/export, and SOC relate? Paired kW timeline with balance and source labels. |
| Flexibility Assessment | How much up/down grid response, when, for how long? kW-by-time envelopes, asset attribution, service windows, uncertainty status. |
| Forecasts | What is expected and how wrong has it been? Forecast versus held-out actual, interval band if calibrated, error by condition. |
| Optimization | What changes and what constraints bind? Baseline/rule/optimized schedules, solver status, service and SOC traces. |
| Recommendations | Which action, when, why, with what tested reliability? Structured evidence card and no-action state. |
| Scenario Lab | What if capacity, tariff, weather, or data quality changes? Paired scenario deltas and tradeoff charts. |
| Experiments | Do claims survive repeated seeds/periods? Protocol, comparisons, failures, reproducibility key. |
| Research Report | Can an operator/researcher audit the conclusion? Download summary plus provenance, assumptions, limitations. |

Use absolute and relative values with units, never percentage-only claims. Visualize intervals as bands with stated method and sample count; `unknown` is visible. Avoid color alone for status. Tooltips define baseline, feasible versus reliable flexibility, and simulated versus measured outcomes. A failed run should display reason and safe next action instead of a blank chart.

## Research report export

The downloadable versioned report contains site and period, data inventory/provenance/quality, asset constraints, baseline definition, feasible and tested reliable flexibility by direction/window, forecast backtest and interval status, solver status and validated schedule, scenario comparisons and all worsened metrics, uncertainty method/sample size, recommendations, limitations, next measurements, dataset/config hashes and software versions. Each figure references the run and units. The report distinguishes synthetic results from observed data on its first page.
