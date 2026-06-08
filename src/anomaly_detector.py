"""
Anomaly detection for the Behavioral Insight Engine.

Applies three complementary statistical methods to identify unusual
observations in each behavioural metric:

1. **Z-score** — flags values whose absolute z-score exceeds
   :data:`config.ZSCORE_THRESHOLD`.
2. **IQR** — flags values outside
   ``[Q1 − 1.5·IQR, Q3 + 1.5·IQR]``.
3. **Rolling deviation** — flags values that deviate from a rolling
   mean by more than :data:`config.ROLLING_DEVIATION_THRESHOLD`
   rolling standard deviations.

An observation is reported as an :class:`Anomaly` if **any** method
triggers.  Explanations are human-readable and cite the expected range
together with the observed deviation.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from models import Anomaly
from config import (
    ZSCORE_THRESHOLD,
    IQR_MULTIPLIER,
    ROLLING_DEVIATION_WINDOW,
    ROLLING_DEVIATION_THRESHOLD,
    MIN_OBSERVATIONS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _zscore_flags(values: pd.Series) -> dict[int, float]:
    """Return index → z-score for values exceeding the threshold.

    Parameters
    ----------
    values:
        Numeric series (may contain NaN; they are ignored).

    Returns
    -------
    dict[int, float]
        Mapping of positional index to the computed z-score for every
        observation that exceeds ``ZSCORE_THRESHOLD``.
    """
    clean = values.dropna()
    if len(clean) < 2:
        return {}

    mean = float(clean.mean())
    std = float(clean.std(ddof=1))

    if std == 0:
        logger.debug("Z-score skipped — standard deviation is zero.")
        return {}

    flagged: dict[int, float] = {}
    for idx in clean.index:
        z = (clean[idx] - mean) / std
        if abs(z) > ZSCORE_THRESHOLD:
            flagged[idx] = round(float(z), 4)
    return flagged


def _iqr_flags(values: pd.Series) -> dict[int, tuple[float, float]]:
    """Return index → (lower_bound, upper_bound) for IQR outliers.

    Parameters
    ----------
    values:
        Numeric series.

    Returns
    -------
    dict[int, tuple[float, float]]
        Mapping of positional index to the ``(lower, upper)`` IQR
        bounds for every observation that falls outside.
    """
    clean = values.dropna()
    if len(clean) < 4:
        return {}

    q1 = float(clean.quantile(0.25))
    q3 = float(clean.quantile(0.75))
    iqr = q3 - q1

    lower = q1 - IQR_MULTIPLIER * iqr
    upper = q3 + IQR_MULTIPLIER * iqr

    flagged: dict[int, tuple[float, float]] = {}
    for idx in clean.index:
        val = float(clean[idx])
        if val < lower or val > upper:
            flagged[idx] = (round(lower, 2), round(upper, 2))
    return flagged


def _rolling_deviation_flags(
    values: pd.Series,
) -> dict[int, tuple[float, float]]:
    """Return index → (rolling_mean, rolling_std) for rolling-deviation outliers.

    Parameters
    ----------
    values:
        Numeric series (NaN values are kept for rolling calculation
        alignment but NaN rows are not flagged).

    Returns
    -------
    dict[int, tuple[float, float]]
        Mapping of positional index to ``(rolling_mean, rolling_std)``
        for every observation that exceeds the rolling-deviation threshold.
    """
    if values.dropna().shape[0] < ROLLING_DEVIATION_WINDOW:
        logger.debug(
            "Rolling deviation skipped — fewer than %d non-NaN values.",
            ROLLING_DEVIATION_WINDOW,
        )
        return {}

    rolling_mean = values.rolling(
        window=ROLLING_DEVIATION_WINDOW, min_periods=ROLLING_DEVIATION_WINDOW
    ).mean()
    rolling_std = values.rolling(
        window=ROLLING_DEVIATION_WINDOW, min_periods=ROLLING_DEVIATION_WINDOW
    ).std(ddof=1)

    flagged: dict[int, tuple[float, float]] = {}
    for idx in values.index:
        val = values[idx]
        r_mean = rolling_mean.get(idx)
        r_std = rolling_std.get(idx)

        if pd.isna(val) or pd.isna(r_mean) or pd.isna(r_std):
            continue
        if r_std == 0:
            continue

        if abs(val - r_mean) > ROLLING_DEVIATION_THRESHOLD * r_std:
            flagged[idx] = (round(float(r_mean), 4), round(float(r_std), 4))

    return flagged


def _build_explanation(
    metric: str,
    observed: float,
    global_mean: float,
    global_std: float,
    z_score: float | None,
    iqr_bounds: tuple[float, float] | None,
) -> str:
    """Produce a human-readable anomaly explanation.

    Parameters
    ----------
    metric:
        Name of the behavioural metric.
    observed:
        The anomalous observed value.
    global_mean:
        The global mean for the metric.
    global_std:
        The global standard deviation for the metric.
    z_score:
        The z-score if z-score method triggered, else ``None``.
    iqr_bounds:
        ``(lower, upper)`` IQR bounds if IQR method triggered, else ``None``.

    Returns
    -------
    str
        A concise, evidence-backed explanation string.
    """
    direction = "above" if observed > global_mean else "below"

    # Prefer IQR range for the "expected range" if available
    if iqr_bounds is not None:
        expected_range = f"{iqr_bounds[0]:.0f}–{iqr_bounds[1]:.0f}"
    else:
        lower_range = global_mean - 2 * global_std
        upper_range = global_mean + 2 * global_std
        expected_range = f"{lower_range:.0f}–{upper_range:.0f}"

    deviation_str = ""
    if z_score is not None:
        deviation_str = (
            f" ({abs(z_score):.1f} standard deviations {direction} mean)"
        )

    qualifier = "high" if observed > global_mean else "low"

    explanation = (
        f"{metric} unusually {qualifier}: observed {observed:.0f} vs "
        f"expected range {expected_range}{deviation_str}"
    )
    return explanation


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_anomalies(
    df: pd.DataFrame,
    metric_columns: list[str],
) -> list[Anomaly]:
    """Detect anomalous observations across all requested metrics.

    For each metric three detection methods are applied independently:

    * **Z-score**: global z-score exceeding ``ZSCORE_THRESHOLD``.
    * **IQR**: value outside ``[Q1 − 1.5·IQR, Q3 + 1.5·IQR]``.
    * **Rolling deviation**: deviation from rolling mean exceeding
      ``ROLLING_DEVIATION_THRESHOLD`` rolling standard deviations.

    An :class:`Anomaly` is emitted whenever *any* method triggers.

    Parameters
    ----------
    df:
        Chronologically sorted DataFrame (must include a parseable date
        column; the date column is auto-detected as the first
        ``datetime64`` column).
    metric_columns:
        Names of the numeric metric columns to analyse.

    Returns
    -------
    list[Anomaly]
        List of detected anomalies sorted chronologically.
    """
    # Auto-detect date column
    date_col: str | None = None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_col = col
            break

    if date_col is None:
        # Fallback: look for a column named 'date' (case-insensitive)
        for col in df.columns:
            if "date" in col.lower():
                date_col = col
                break

    anomalies: list[Anomaly] = []

    for metric in metric_columns:
        if metric not in df.columns:
            logger.warning("Metric '%s' not in DataFrame; skipping.", metric)
            continue

        series = df[metric]
        clean = series.dropna()

        if len(clean) < MIN_OBSERVATIONS:
            logger.warning(
                "Metric '%s' has only %d non-NaN values (need %d); "
                "skipping anomaly detection.",
                metric,
                len(clean),
                MIN_OBSERVATIONS,
            )
            continue

        global_mean = float(clean.mean())
        global_std = float(clean.std(ddof=1))

        # ---- Run all three methods -----------------------------------
        z_flags = _zscore_flags(series)
        iqr_flags = _iqr_flags(series)
        rolling_flags = _rolling_deviation_flags(series)

        # ---- Merge flags for each row --------------------------------
        all_flagged_indices = set(z_flags) | set(iqr_flags) | set(rolling_flags)

        for idx in all_flagged_indices:
            observed = float(series[idx])

            methods_triggered: list[str] = []
            if idx in z_flags:
                methods_triggered.append("z_score")
            if idx in iqr_flags:
                methods_triggered.append("iqr")
            if idx in rolling_flags:
                methods_triggered.append("rolling_deviation")

            z_val = z_flags.get(idx)
            iqr_bounds = iqr_flags.get(idx)

            # Compute z-score even if z-score method didn't trigger
            # (used for the deviation field).
            if z_val is not None:
                deviation = z_val
            elif global_std > 0:
                deviation = round((observed - global_mean) / global_std, 4)
            else:
                deviation = 0.0

            explanation = _build_explanation(
                metric=metric,
                observed=observed,
                global_mean=global_mean,
                global_std=global_std,
                z_score=z_val if z_val is not None else (
                    deviation if global_std > 0 else None
                ),
                iqr_bounds=iqr_bounds,
            )

            # Resolve date string
            if date_col is not None and date_col in df.columns:
                date_value = df[date_col].iloc[idx]
                if pd.api.types.is_datetime64_any_dtype(
                    df[date_col]
                ):
                    date_str = pd.Timestamp(date_value).strftime("%Y-%m-%d")
                else:
                    date_str = str(date_value)
            else:
                date_str = f"row-{idx}"

            anomaly = Anomaly(
                date=date_str,
                metric=metric,
                observed_value=round(observed, 4),
                expected_value=round(global_mean, 4),
                deviation=round(deviation, 4),
                methods_triggered=methods_triggered,
                explanation=explanation,
            )
            anomalies.append(anomaly)

    # Sort anomalies chronologically by date
    anomalies.sort(key=lambda a: a.date)

    logger.info(
        "Anomaly detection complete: %d anomaly/anomalies found across "
        "%d metric(s).",
        len(anomalies),
        len(metric_columns),
    )
    return anomalies
