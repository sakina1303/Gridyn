# Forecast experiment plan

Forecast targets: PV available kW and nonflexible/critical site load kW at 15 min intervals, 24 h ahead. EV/pump/HVAC obligations remain operator-declared or scenario variables until session data justify forecasting. Use rolling-origin train/calibration/test splits with weather forecasts that would have been available at issue time.

Models: previous-day/week persistence; hour/day moving average; regularized linear regression with calendar/weather features; random forest or histogram gradient boosting. XGBoost may be compared later if the simple tree model shows a need. No LSTM in MVP. Missing data imputation and scaling fit only on each training fold. Evaluate across clear/cloudy, weekday/weekend and high/low cooling conditions.

Metrics: MAE/RMSE (kW), MAPE only on positive appropriate target, prediction-interval coverage/width if calibrated. Downstream: envelope overstatement (kW), realized cost/peak/service under the identical optimizer and truth, hard violations, recommendation changes under small input perturbations, and decision regret relative to persistence and perfect-information bound. Predeclare a tolerance for practically meaningful improvement after inspecting typical site scale but before test evaluation. A model with lower RMSE but worse service or regret is not promoted. Report inference/training burden and all negative results.
