"""Leakage-free persistence checks on paired observed load and PV series.

Indexing follows consecutive source 15-minute slots. No UTC timezone, site
import, PV availability, or asset service is inferred from source readings.
"""

from __future__ import annotations

import math


INTERVALS_PER_DAY = 96
METHOD_LAGS = {"previous_day": 1, "previous_week": 7}


def evaluate_paired_series(series: dict[str, tuple[float | None, ...]], *,
                           first_test_day: int, test_days: int,
                           evaluation_windows: dict[str, tuple[int, int]] | None = None) -> dict:
    if set(series) not in ({"consumer_load_kw", "pv_output_kw"}, {"building_load_kw", "pv_output_kw"}):
        raise ValueError("paired observed load and PV series are required")
    lengths = {len(values) for values in series.values()}
    if len(lengths) != 1 or first_test_day < 7 or test_days < 1:
        raise ValueError("aligned series and at least seven training days are required")
    length = lengths.pop()
    if (first_test_day + test_days) * INTERVALS_PER_DAY > length:
        raise ValueError("test days exceed the observed series")
    windows = evaluation_windows or {}
    if any(name not in series or not (0 <= start < end <= INTERVALS_PER_DAY)
           for name, (start, end) in windows.items()):
        raise ValueError("invalid evaluation window")
    for values in series.values():
        if any(value is not None and (not math.isfinite(value) or value < 0) for value in values):
            raise ValueError("observed gross power must be finite and nonnegative")

    folds = []
    for signal, values in series.items():
        window_start, window_end = windows.get(signal, (0, INTERVALS_PER_DAY))
        for day in range(first_test_day, first_test_day + test_days):
            start = day * INTERVALS_PER_DAY + window_start
            count = window_end - window_start
            actual = values[start:start + count]
            for method, lag_days in METHOD_LAGS.items():
                prior = values[start - lag_days * INTERVALS_PER_DAY:
                               start - lag_days * INTERVALS_PER_DAY + count]
                row = {"signal": signal, "test_day_index": day, "method": method,
                       "window_slot_start": window_start, "window_slot_end": window_end,
                       "status": "abstained", "reason": None, "evaluated_intervals": 0,
                       "mae_kw": None, "absolute_scored_peak_error_kw": None}
                if any(value is None for value in actual):
                    row["reason"] = "incomplete held-out day"
                elif any(value is None for value in prior):
                    row["reason"] = f"incomplete {method} training day"
                else:
                    errors = [prediction - observed for prediction, observed in zip(prior, actual)]
                    row.update({"status": "evaluated", "reason": None,
                                "evaluated_intervals": count,
                                "mae_kw": sum(abs(error) for error in errors) / count,
                                "absolute_scored_peak_error_kw": abs(max(prior) - max(actual))})
                folds.append(row)
    summaries = []
    for signal in series:
        for method in METHOD_LAGS:
            rows = [row for row in folds if row["signal"] == signal and row["method"] == method]
            evaluated = [row for row in rows if row["status"] == "evaluated"]
            summaries.append({"signal": signal, "method": method,
                              "window_slot_start": windows.get(signal, (0, INTERVALS_PER_DAY))[0],
                              "window_slot_end": windows.get(signal, (0, INTERVALS_PER_DAY))[1],
                              "evaluated_days": len(evaluated), "abstained_days": len(rows) - len(evaluated),
                              "mean_mae_kw": sum(row["mae_kw"] for row in evaluated) / len(evaluated) if evaluated else None,
                              "mean_absolute_scored_peak_error_kw":
                              sum(row["absolute_scored_peak_error_kw"] for row in evaluated) / len(evaluated)
                              if evaluated else None})
    return {"folds": folds, "summaries": summaries}
