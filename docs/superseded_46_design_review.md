# Cross-document design review

Review date: 22 October 2026. Scope: [21–45](21_product_definition.md). This review is superseded by [45_design_review.md](45_design_review.md) and kept for history; it does not claim validation of the product hypothesis.

| Issue found | Resolution in design | Remaining gate |
|---|---|---|
| Broad optimizer positioning duplicates existing tools | [21](21_product_definition.md), [32](32_research_contribution.md), and [44](44_final_architecture_decision.md) define a sparse-data reliability question instead | Deeper prior-art review and operator interviews |
| “Reliable” could be mistaken for a field guarantee | [22](22_flexibility_model.md) defines scenario deliverability; [23](23_uncertainty_framework.md) requires calibration/provenance; UI shows `unknown` | Real shadow validation |
| Sparse data could feed an overconfident optimizer | [24](24_data_readiness.md) gates claims; [41](41_failure_modes.md) suppresses unsafe recommendations | Test ablations and abstention usefulness |
| Site model might imply feeder/voltage benefits | [21](21_product_definition.md), [39](39_pilot_plan.md), and [44](44_final_architecture_decision.md) exclude these claims | Network data/model in later research |
| Battery and grid directions could be physically inconsistent | [27](27_optimization_model.md) uses direction binaries and [38](38_validation_strategy.md) recomputes residuals | Solver implementation tests |
| Too many UI screens could bloat MVP | [33](33_mvp_scope.md) and [37](37_ui_spec.md) collapse to five primary flows | Usability feedback |
| PostgreSQL/Docker could delay science | [34](34_system_architecture.md) permits portable SQLite locally and defers packaging | Choose at implementation setup |
| HVAC thermal model could imply unsupported precision | [22](22_flexibility_model.md) and [34](34_system_architecture.md) use conservative windows until calibrated | Obtain thermal/comfort data |
| Cost claims may use a made-up tariff | [24](24_data_readiness.md), [30](30_scenario_engine.md), and [40](40_success_metrics.md) label conditional synthetic tariffs | Verify state/category order |
| Historical replay may be mistaken for realized impact | [38](38_validation_strategy.md) distinguishes simulation, retrospective and prospective evidence | Controlled or shadow pilot |

No application code was produced. The architecture is internally coherent as a **conditional research prototype design**, but the user/problem fit and novelty are unverified. The prior dependency order is in [the superseded plan](superseded_45_implementation_plan.md); the current order is in [58](58_implementation_plan.md). If stage-0 interviews or prior-art review overturn the gap, revise [21](21_product_definition.md), [32](32_research_contribution.md), and [44](44_final_architecture_decision.md) before implementation.
