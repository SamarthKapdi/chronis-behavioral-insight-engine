"""
Pattern detection for the Behavioral Insight Engine.

Detects behavioural trends by combining two complementary methods:

1. **Window comparison** — compares the recent 7-day mean against the
   previous 7-day mean to compute a percent change and classify the
   trend direction.
2. **Linear regression** — fits ``scipy.stats.linregress`` on the full
   time series to obtain a slope, *R²*, and *p*-value.

The two signals are merged into a single :class:`TrendResult` per metric,
with ``supporting_statistics`` that document agreement between methods.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from models import TrendResult
from config import (
    ROLLING_WINDOW_SIZE,
    TREND_THRESHOLD_PERCENT,
    REGRESSION_P_VALUE_THRESHOLD,
    MIN_OBSERVATIONS,
)
from feature_engineering import get_metric_series

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_direction(percent_change: float) -> str:
    """Map a percent change to a trend direction label.

    Parameters
    ----------
    percent_change:
        The computed percent change (recent vs. previous window).

    Returns
    -------
    str
        ``'increasing'``, ``'decreasing'``, or ``'stable'``.
    """
    if percent_change > TREND_THRESHOLD_PERCENT:
        return "increasing"
    if percent_change < -TREND_THRESHOLD_PERCENT:
        return "decreasing"
    return "stable"


def _regression_direction(slope: float) -> str:
    """Derive a directional label from the regression slope sign.

    Parameters
    ----------
    slope:
        Linear regression slope.

    Returns
    -------
    str
        ``'increasing'`` if slope > 0, ``'decreasing'`` if slope < 0,
        otherwise ``'stable'``.
    """
    if slope > 0:
        return "increasing"
    if slope < 0:
        return "decreasing"
    return "stable"


def _count_days_in_direction(
    recent_values: list[float], direction: str
) -> int:
    """Count how many days in the recent window moved in *direction*.

    A day "moves in direction" when its value is greater than (for
    ``'increasing'``) or less than (for ``'decreasing'``) the
    preceding day's value.

    Parameters
    ----------
    recent_values:
        Ordered list of recent metric values.
    direction:
        ``'increasing'``, ``'decreasing'``, or ``'stable'``.

    Returns
    -------
    int
        Number of day-over-day changes that match *direction*.
    """
    if len(recent_values) < 2 or direction == "stable":
        return 0

    count = 0
    for i in range(1, len(recent_values)):
        diff = recent_values[i] - recent_values[i - 1]
        if direction == "increasing" and diff > 0:
            count += 1
        elif direction == "decreasing" and diff < 0:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_patterns(
    df: pd.DataFrame,
    metric_columns: list[str],
) -> list[TrendResult]:
    """Detect behavioural trends across all requested metrics.

    For each metric the function performs:

    * **Window comparison** using the last ``ROLLING_WINDOW_SIZE`` rows
      as *recent* and the preceding window as *previous*.
    * **Linear regression** on the full time series (NaN-free).

    Both results are merged into a single :class:`TrendResult`.

    Parameters
    ----------
    df:
        Chronologically sorted DataFrame.
    metric_columns:
        Names of the numeric metric columns to analyse.

    Returns
    -------
    list[TrendResult]
        One ``TrendResult`` per metric that had sufficient data.
    """
    results: list[TrendResult] = []
    window = ROLLING_WINDOW_SIZE

    for metric in metric_columns:
        # --- Extract clean series ----------------------------------------
        try:
            series = get_metric_series(df, metric)
        except KeyError:
            logger.warning("Metric '%s' not found; skipping.", metric)
            continue

        if len(series) < MIN_OBSERVATIONS:
            logger.warning(
                "Metric '%s' has only %d non-NaN values (need %d); skipping.",
                metric,
                len(series),
                MIN_OBSERVATIONS,
            )
            continue

        values = series.values.astype(float)

        # =================================================================
        # A. Window comparison
        # =================================================================
        if len(values) >= 2 * window:
            recent_vals = values[-window:]
            previous_vals = values[-2 * window : -window]
        else:
            # Graceful fallback: split available data in half
            mid = len(values) // 2
            previous_vals = values[:mid]
            recent_vals = values[mid:]

        recent_mean = float(np.mean(recent_vals))
        previous_mean = float(np.mean(previous_vals))

        if previous_mean != 0:
            percent_change = (
                (recent_mean - previous_mean) / abs(previous_mean)
            ) * 100.0
        else:
            # Avoid division by zero — use absolute change as surrogate
            percent_change = float(recent_mean - previous_mean) * 100.0
            logger.debug(
                "Metric '%s': previous_mean is zero; using absolute change "
                "as percent_change surrogate (%.2f).",
                metric,
                percent_change,
            )

        trend_direction = _classify_direction(percent_change)

        # =================================================================
        # B. Linear regression on full series
        # =================================================================
        x = np.arange(len(values), dtype=float)
        reg = sp_stats.linregress(x, values)
        slope = float(reg.slope)
        r_squared = float(reg.rvalue ** 2)
        p_value = float(reg.pvalue)

        regression_significant = p_value < REGRESSION_P_VALUE_THRESHOLD
        regression_dir = _regression_direction(slope)
        methods_agree = trend_direction == regression_dir

        # =================================================================
        # Supporting statistics
        # =================================================================
        days_in_direction = _count_days_in_direction(
            recent_vals.tolist(), trend_direction
        )

        supporting_statistics: dict[str, Any] = {
            "window_comparison_pct": round(percent_change, 4),
            "regression_slope": round(slope, 6),
            "regression_significant": regression_significant,
            "methods_agree": methods_agree,
            "days_in_trend_direction": days_in_direction,
        }

        trend = TrendResult(
            metric=metric,
            trend_direction=trend_direction,
            percent_change=round(percent_change, 4),
            slope=round(slope, 6),
            r_squared=round(r_squared, 4),
            p_value=round(p_value, 6),
            recent_mean=round(recent_mean, 4),
            previous_mean=round(previous_mean, 4),
            supporting_statistics=supporting_statistics,
        )
        results.append(trend)

        logger.info(
            "Metric '%s': direction=%s, pct_change=%.2f%%, "
            "slope=%.4f, R2=%.4f, p=%.4f, methods_agree=%s",
            metric,
            trend_direction,
            percent_change,
            slope,
            r_squared,
            p_value,
            methods_agree,
        )

    logger.info(
        "Pattern detection complete: %d trend(s) detected across %d metric(s).",
        len(results),
        len(metric_columns),
    )
    return results
