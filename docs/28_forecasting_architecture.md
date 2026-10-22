# Forecasting architecture

**Implementation authority:** [46_canonical_model.md](46_canonical_model.md) and [55_forecast_experiment_plan.md](55_forecast_experiment_plan.md). The first comparison issues a 24-hour forecast on the same decision grid as the optimizer.

Forecast 15/30/60 minute available PV and **uncontrolled** site load separately; do not train demand on already optimized load without a treatment flag. For flexible EV/HVAC/pump demand, forecast availability/required service only if data exist; otherwise use declared scenarios. Prediction objects carry horizon, timestep, units, training cutoff, model version, point value and optional interval.

Baselines: same time previous day/week persistence, seasonal moving average, and simple physical solar shape with weather when available. Candidates: regularized linear regression and random forest or gradient boosting. XGBoost is optional only if it wins a time-split comparison at acceptable complexity. LSTM is out of MVP absent enough data and a demonstrated advantage. This follows the decision problem rather than an AI label.

Use rolling-origin evaluation: train before `τ`, predict the next 24–48 hours, advance `τ`; keep final weeks/seasons untouched. Compare MAE and RMSE in kW, normalized error when denominators are meaningful, and MAPE only for strictly positive load segments (never night PV). For intervals, report empirical coverage and mean width; evaluate peak/event windows separately. Also evaluate **decision regret**: run the optimizer with each forecast, replay against actual/synthetic truth, and compare delivered service and objective with perfect-information and persistence baselines. A lower RMSE with no decision benefit is not a product win.

Leakage controls: weather forecast available at issue time, not observed future weather; no random cross-validation of adjacent intervals; no test-period fitting of imputation, scaling, or interval calibration; record missing-data flags. When evidence is insufficient, output a scenario range and `not calibrated` rather than a prediction interval.
