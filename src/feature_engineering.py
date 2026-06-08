"""
Feature engineering for the Behavioral Insight Engine.

Provides rolling-window statistics that compare a *recent* window of
observations against a *previous* window, enabling downstream modules
to quantify short-term behavioural shifts.

Functions
---------
compute_rolling_stats
    Compute :class:`RollingStats` for every requested metric.
get_metric_series
    Extract a single metric as a NaN-free ``pd.Series``.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from models import RollingStats
from config import ROLLING_WINDOW_SIZE
from exceptions import InsufficientDataError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_rolling_stats(
    df: pd.DataFrame,
    metric_columns: list[str],
    window_size: int = ROLLING_WINDOW_SIZE,
) -> dict[str, RollingStats]:
    """Compute recent-vs-previous rolling statistics for each metric.

    For every metric the function extracts two contiguous windows from
    the tail of the (chronologically sorted) DataFrame:

    * **Recent window** — the last *window_size* rows.
    * **Previous window** — the *window_size* rows immediately before
      the recent window.

    If either window for a given metric contains more than 50 % NaN
    values the metric is silently skipped with a warning.

    Parameters
    ----------
    df:
        Chronologically sorted DataFrame produced by ``load_behavioral_data``.
    metric_columns:
        Column names of the numeric metrics to analyse.
    window_size:
        Size of each comparison window (defaults to
        :data:`config.ROLLING_WINDOW_SIZE`).

    Returns
    -------
    dict[str, RollingStats]
        Mapping of metric name → ``RollingStats`` for every metric that
        had sufficient data in both windows.

    Raises
    ------
    InsufficientDataError
        If the DataFrame has fewer than ``2 * window_size`` rows.
    """
    required_rows = 2 * window_size
    if len(df) < required_rows:
        raise InsufficientDataError(
            f"DataFrame has {len(df)} rows, but at least {required_rows} "
            f"are required for a window size of {window_size}."
        )

    results: dict[str, RollingStats] = {}

    for metric in metric_columns:
        if metric not in df.columns:
            logger.warning(
                "Metric '%s' not found in DataFrame columns; skipping.", metric
            )
            continue

        recent_raw: pd.Series = df[metric].iloc[-window_size:]
        previous_raw: pd.Series = df[metric].iloc[-2 * window_size : -window_size]

        # Guard against excessive NaN values (>50 %)
        max_nans = window_size // 2
        recent_nans = int(recent_raw.isna().sum())
        previous_nans = int(previous_raw.isna().sum())

        if recent_nans > max_nans or previous_nans > max_nans:
            logger.warning(
                "Metric '%s' skipped — too many NaN values "
                "(recent: %d, previous: %d, threshold: %d).",
                metric,
                recent_nans,
                previous_nans,
                max_nans,
            )
            continue

        recent_clean = recent_raw.dropna()
        previous_clean = previous_raw.dropna()

        recent_values = recent_clean.tolist()
        previous_values = previous_clean.tolist()

        recent_mean = float(np.mean(recent_values))
        previous_mean = float(np.mean(previous_values))
        recent_std = float(np.std(recent_values, ddof=1)) if len(recent_values) > 1 else 0.0
        previous_std = float(np.std(previous_values, ddof=1)) if len(previous_values) > 1 else 0.0

        stats = RollingStats(
            metric=metric,
            recent_values=recent_values,
            previous_values=previous_values,
            recent_mean=recent_mean,
            previous_mean=previous_mean,
            recent_std=recent_std,
            previous_std=previous_std,
        )
        results[metric] = stats

        logger.debug(
            "RollingStats for '%s': recent_mean=%.3f, previous_mean=%.3f, "
            "recent_std=%.3f, previous_std=%.3f",
            metric,
            recent_mean,
            previous_mean,
            recent_std,
            previous_std,
        )

    logger.info(
        "Computed rolling stats for %d of %d metric(s).",
        len(results),
        len(metric_columns),
    )
    return results


def get_metric_series(df: pd.DataFrame, metric: str) -> pd.Series:
    """Extract a single metric column as a NaN-free Series.

    This is a convenience helper used by downstream modules that need
    a clean numeric series for statistical computation.

    Parameters
    ----------
    df:
        Source DataFrame.
    metric:
        Name of the metric column to extract.

    Returns
    -------
    pd.Series
        The metric column with NaN values removed, preserving the
        original index.

    Raises
    ------
    KeyError
        If *metric* is not present in *df*.
    """
    if metric not in df.columns:
        raise KeyError(f"Metric column '{metric}' not found in DataFrame.")

    series = df[metric].dropna()
    logger.debug(
        "Extracted metric '%s': %d values (%d NaN dropped).",
        metric,
        len(series),
        len(df) - len(series),
    )
    return series
