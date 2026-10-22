# Final implementation gate

| Gate question | Decision and evidence |
|---|---|
| Architecture internally consistent? | **Yes for simulation-first scope.** [45](45_design_review.md) resolves convention ambiguities; [44](44_final_architecture_decision.md) governs product scope. |
| Canonical energy model defined? | **Yes.** [46](46_canonical_model.md) fixes signs, units, intervals, SOC, balance, service and terminal treatment. |
| Simulator can generate reproducible truth? | **Specified, not implemented.** [47](47_simulator_spec.md)–[48](48_synthetic_dataset_spec.md) define deterministic generation and checksums. Implementation ticket T07–T12 must prove it. |
| Observed data derived from truth? | **Specified, not implemented.** Separate observation operator, seed and access boundary in [47–48](47_simulator_spec.md). |
| Research question experimentally testable? | **Yes in simulation.** Ablations [25](25_minimum_data_experiments.md), uncertainty matrix [54](54_uncertainty_experiment_matrix.md), and paired hierarchy [52](52_baseline_hierarchy.md) define ground truth and metrics. |
| MVP possible without facility data? | **Yes, as a simulation-only research prototype.** Real-world generalization remains unvalidated. |
| Claims measurable? | **Yes, conditional on implementation.** [40](40_success_metrics.md), [50](50_response_envelope.md), and [57](57_report_schema.md) define denominators/provenance. |
| Success/failure conditions defined? | **Yes.** [40](40_success_metrics.md), [41](41_failure_modes.md), [60](60_testing_strategy.md), and [61](61_numerical_validation.md). |
| Unresolved decisions that prevent first implementation? | **No.** First work is canonical units and simulator. Solver installation/performance, tariff selection, operator interviews, real dataset access and prior-art depth are later gates, not excuses to invent results. |

## Mandatory stop conditions during build

Stop dependent phases if power balance, critical service, SOC, deterministic replay, truth/observation separation, or baseline validity fails. Stop field claims until consented data, applicable tariff, operator validation and credible external evaluation exist. Stop novelty claims until deeper prior-art review. If the solver cannot produce validated feasible schedules within the bounded fixture, reconsider model/solver before UI integration.

**READY TO BUILD** the phased, advisory **simulation research prototype** described here. This is a planning gate, not authorization to start coding in this turn; the current request explicitly prohibits implementation.
