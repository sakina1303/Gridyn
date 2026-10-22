# Technical debt and scope boundary

Do **not** engineer now: real-time actuation, SCADA/ADMS integration, voltage/AC power flow, feeder protection, frequency services, market bids/settlement, VPP orchestration, live DISCOM or India Energy Stack API, automated tariff scraping, detailed battery chemistry/degradation, nonlinear HVAC physics without calibration, deep learning, LLM numerical explanations, multi-tenant SaaS, complex authentication, mobile app, blockchain, or commercial billing.

Allowed substitutes: static import/export connection cap rather than network model; simple battery throughput proxy labeled as such; conservative HVAC operating window; versioned manually entered tariff scenario; deterministic synthetic data; local SQLite/files; rule-based explanation templates. Record each substitute in run provenance and limitations. Architectural seams (typed dataset, solver adapter, asset model) allow later research without building speculative integrations now.

Scope change rule: a proposed feature must state which research hypothesis or MVP acceptance gate it enables, what data it needs, and what existing phase it displaces. If it does not improve physical validity, data efficiency, uncertainty evaluation, or operator decision quality, defer it.
