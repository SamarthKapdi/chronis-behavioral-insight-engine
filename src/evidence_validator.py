"""
Evidence sufficiency validator for the Behavioral Insight Engine.

Before generating any insight, the engine must confirm that the
underlying data meets minimum quality thresholds.  This module
encapsulates three independent checks:

1. **Sample size** — enough non-missing observations to be meaningful.
2. **Variance** — the data must exhibit meaningful variation (not flat).
3. **Signal strength** — the detected trend magnitude must exceed a
   minimum threshold to avoid reporting noise as a finding.

All thresholds are sourced from ``config.py`` so they can be tuned
without modifying validation logic.
"""

from __future__ import annotations

import logging
from typing import Union

import numpy as np
import pandas as pd

from config import (
    MIN_COEFFICIENT_OF_VARIATION,
    MIN_OBSERVATIONS,
    MIN_TREND_MAGNITUDE_PERCENT,
)
from models import EvidenceResult

logger = logging.getLogger(__name__)


def validate_evidence(
    values: Union[pd.Series, list[float]],
    metric: str,
    percent_change: float,
) -> EvidenceResult:
    """Validate whether a metric's data provides sufficient evidence for insight generation.

    Three independent checks are performed:

    1. **Sample size**: the number of valid (non-NaN) observations must be
       at least ``MIN_OBSERVATIONS``.
    2. **Coefficient of variation**: ``std / mean`` must exceed
       ``MIN_COEFFICIENT_OF_VARIATION`` to ensure the data is not
       effectively constant.
    3. **Signal strength**: ``|percent_change|`` must be at least
       ``MIN_TREND_MAGNITUDE_PERCENT`` so we avoid reporting trivial
       fluctuations.

    Args:
        values: Raw metric values (NaNs are dropped before analysis).
        metric: Human-readable metric name for logging and reporting.
        percent_change: Percent change detected by the pattern detector.

    Returns:
        An ``EvidenceResult`` summarising whether all checks passed and,
        if not, the specific reasons for each failure.
    """
    # Normalise to a NumPy array, dropping NaN values.
    if isinstance(values, pd.Series):
        clean_values = values.dropna().to_numpy(dtype=float)
    else:
        clean_values = np.array(values, dtype=float)
        clean_values = clean_values[~np.isnan(clean_values)]

    sample_size: int = len(clean_values)
    reasons: list[str] = []

    # ------------------------------------------------------------------
    # Check 1 — Minimum sample size
    # ------------------------------------------------------------------
    has_sufficient_observations: bool = sample_size >= MIN_OBSERVATIONS
    if not has_sufficient_observations:
        reason = (
            f"Insufficient observations: {sample_size} < "
            f"{MIN_OBSERVATIONS} required"
        )
        reasons.append(reason)
        logger.info("Evidence check failed for '%s': %s", metric, reason)

    # ------------------------------------------------------------------
    # Check 2 — Minimum coefficient of variation
    # ------------------------------------------------------------------
    if sample_size > 0:
        mean_val: float = float(np.mean(clean_values))
        std_val: float = float(np.std(clean_values, ddof=0))
        cv: float = std_val / mean_val if mean_val != 0 else 0.0
    else:
        cv = 0.0

    has_sufficient_variance: bool = cv > MIN_COEFFICIENT_OF_VARIATION
    if not has_sufficient_variance:
        reason = (
            f"Insufficient variance: coefficient of variation "
            f"{cv:.4f} below threshold {MIN_COEFFICIENT_OF_VARIATION}"
        )
        reasons.append(reason)
        logger.info("Evidence check failed for '%s': %s", metric, reason)

    # ------------------------------------------------------------------
    # Check 3 — Minimum trend magnitude
    # ------------------------------------------------------------------
    pct: float = abs(percent_change)
    has_sufficient_signal: bool = pct >= MIN_TREND_MAGNITUDE_PERCENT
    if not has_sufficient_signal:
        reason = (
            f"Trend magnitude too small: {pct:.1f}% below "
            f"{MIN_TREND_MAGNITUDE_PERCENT}% minimum"
        )
        reasons.append(reason)
        logger.info("Evidence check failed for '%s': %s", metric, reason)

    # ------------------------------------------------------------------
    # Aggregate verdict
    # ------------------------------------------------------------------
    is_sufficient: bool = (
        has_sufficient_observations
        and has_sufficient_variance
        and has_sufficient_signal
    )

    if is_sufficient:
        logger.info(
            "Evidence sufficient for '%s': n=%d, cv=%.4f, |change|=%.1f%%",
            metric,
            sample_size,
            cv,
            pct,
        )
    else:
        logger.info(
            "Evidence insufficient for '%s': %d reason(s) - %s",
            metric,
            len(reasons),
            "; ".join(reasons),
        )

    return EvidenceResult(
        metric=metric,
        is_sufficient=is_sufficient,
        sample_size=sample_size,
        has_sufficient_variance=has_sufficient_variance,
        has_sufficient_signal=has_sufficient_signal,
        reasons=reasons,
    )
