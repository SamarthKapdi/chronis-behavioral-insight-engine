"""
Confidence scoring engine for the Behavioral Insight Engine.

Computes a transparent, multi-factor confidence score for each
potential insight.  The score is a weighted combination of four
independently interpretable sub-scores:

* **Sample score** — normalised sample size (saturates at a
  configurable ceiling).
* **Trend score** — normalised absolute percent change.
* **Consistency score** — fraction of day-over-day changes that
  agree with the detected trend direction.
* **Variance score** — inverse of coefficient of variation, rewarding
  stable series where the trend signal is less likely to be noise.

All weights and saturation points are sourced from ``config.py``.
"""

from __future__ import annotations

import logging

import numpy as np

from config import (
    SAMPLE_SIZE_SATURATION,
    TREND_STRENGTH_SATURATION,
    WEIGHT_CONSISTENCY,
    WEIGHT_SAMPLE_SIZE,
    WEIGHT_TREND_STRENGTH,
    WEIGHT_VARIANCE,
)
from models import ConfidenceComponents

logger = logging.getLogger(__name__)


def calculate_confidence(
    sample_size: int,
    percent_change: float,
    daily_values: list[float],
    trend_direction: str,
) -> ConfidenceComponents:
    """Calculate a composite confidence score for a detected trend.

    The final score is a weighted sum of four normalised sub-scores,
    each in the range [0, 1].  The result is clamped to [0, 1].

    Args:
        sample_size: Number of valid observations used in the analysis.
        percent_change: Detected percent change between windows.
        daily_values: Ordered daily metric values (most-recent window).
        trend_direction: ``"increasing"``, ``"decreasing"``, or
            ``"stable"`` as determined by the pattern detector.

    Returns:
        A ``ConfidenceComponents`` instance containing each sub-score
        and the ``final_confidence``.
    """
    # ------------------------------------------------------------------
    # 1. Sample score — saturates at SAMPLE_SIZE_SATURATION
    # ------------------------------------------------------------------
    sample_score: float = min(sample_size / SAMPLE_SIZE_SATURATION, 1.0)

    # ------------------------------------------------------------------
    # 2. Trend score — saturates at TREND_STRENGTH_SATURATION
    # ------------------------------------------------------------------
    trend_score: float = min(
        abs(percent_change) / TREND_STRENGTH_SATURATION, 1.0
    )

    # ------------------------------------------------------------------
    # 3. Consistency score — fraction of days following the trend
    # ------------------------------------------------------------------
    consistency_score: float = _compute_consistency(
        daily_values, trend_direction
    )

    # ------------------------------------------------------------------
    # 4. Variance score — low CV → high confidence
    # ------------------------------------------------------------------
    variance_score: float = _compute_variance_score(daily_values)

    # ------------------------------------------------------------------
    # Weighted combination
    # ------------------------------------------------------------------
    raw_confidence: float = (
        WEIGHT_SAMPLE_SIZE * sample_score
        + WEIGHT_TREND_STRENGTH * trend_score
        + WEIGHT_CONSISTENCY * consistency_score
        + WEIGHT_VARIANCE * variance_score
    )
    final_confidence: float = max(0.0, min(raw_confidence, 1.0))

    logger.debug(
        "Confidence breakdown — sample=%.3f, trend=%.3f, "
        "consistency=%.3f, variance=%.3f → final=%.3f",
        sample_score,
        trend_score,
        consistency_score,
        variance_score,
        final_confidence,
    )

    return ConfidenceComponents(
        sample_score=sample_score,
        trend_score=trend_score,
        consistency_score=consistency_score,
        variance_score=variance_score,
        final_confidence=final_confidence,
    )


# ======================================================================
# Internal helpers
# ======================================================================


def _compute_consistency(
    daily_values: list[float],
    trend_direction: str,
) -> float:
    """Return the fraction of consecutive day-over-day changes matching *trend_direction*.

    Args:
        daily_values: Ordered daily values.
        trend_direction: ``"increasing"``, ``"decreasing"``, or ``"stable"``.

    Returns:
        A float in [0, 1].  Returns 0 when there are fewer than 2 values.
    """
    if len(daily_values) < 2:
        return 0.0

    arr = np.asarray(daily_values, dtype=float)
    total_transitions: int = len(arr) - 1
    matching_days: int = 0

    mean_val: float = float(np.mean(arr)) if len(arr) > 0 else 0.0
    threshold: float = 0.05 * abs(mean_val) if mean_val != 0 else 0.0

    for i in range(1, len(arr)):
        change: float = arr[i] - arr[i - 1]

        if trend_direction == "increasing" and change > 0:
            matching_days += 1
        elif trend_direction == "decreasing" and change < 0:
            matching_days += 1
        elif trend_direction == "stable" and abs(change) < threshold:
            matching_days += 1

    return matching_days / total_transitions


def _compute_variance_score(daily_values: list[float]) -> float:
    """Return a stability score derived from the coefficient of variation.

    Lower CV means more stable data, yielding a higher score.

    Args:
        daily_values: Ordered daily values.

    Returns:
        ``max(1.0 - cv, 0.0)`` where *cv* is capped at 1.0 before
        subtraction.
    """
    if len(daily_values) == 0:
        return 0.0

    arr = np.asarray(daily_values, dtype=float)
    mean_val: float = float(np.mean(arr))

    if mean_val == 0:
        cv: float = 1.0
    else:
        cv = float(np.std(arr, ddof=0)) / abs(mean_val)

    # Cap cv at 1.0 before computing the score.
    cv = min(cv, 1.0)
    return max(1.0 - cv, 0.0)
