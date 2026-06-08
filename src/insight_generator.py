"""
Insight generator for the Behavioral Insight Engine.

This module is the core intelligence layer that transforms raw
statistical results (trends and anomalies) into human-readable,
evidence-backed insights.  It enforces a strict quality gate:

1. **Evidence validation** — the underlying data must pass minimum
   thresholds for sample size, variance, and signal strength.
2. **Confidence scoring** — a weighted composite score must exceed
   the configured threshold before an insight is emitted.
3. **Output safety** — every generated insight text is scanned for
   forbidden terms to prevent diagnostic or stigmatising language.

When any gate fails the engine emits an explicit ``Abstention``
rather than a low-quality or unsafe insight.
"""

from __future__ import annotations

import logging

import pandas as pd

from confidence_engine import calculate_confidence
from config import CONFIDENCE_THRESHOLD, FORBIDDEN_TERMS, ROLLING_WINDOW_SIZE
from evidence_validator import validate_evidence
from models import Abstention, Anomaly, Insight, TrendResult

logger = logging.getLogger(__name__)


def generate_insights(
    patterns: list[TrendResult],
    anomalies: list[Anomaly],
    df: pd.DataFrame,
) -> tuple[list[Insight], list[Abstention]]:
    """Generate evidence-backed insights from detected patterns.

    For every ``TrendResult`` in *patterns* the function:

    1. Extracts the metric's values from *df* (dropping NaN).
    2. Validates evidence sufficiency via ``validate_evidence``.
    3. Computes a confidence score via ``calculate_confidence``.
    4. If both gates pass, builds a templated insight string and
       performs a forbidden-term safety scan.
    5. Otherwise emits an ``Abstention`` with a clear reason.

    Args:
        patterns: Trend results from the pattern detector.
        anomalies: Anomaly results (reserved for future enrichment;
            currently not directly consumed but available for
            cross-referencing in later iterations).
        df: The full behavioural dataset as a DataFrame.

    Returns:
        A tuple ``(insights, abstentions)`` where each list may be
        empty if no patterns were supplied.
    """
    insights: list[Insight] = []
    abstentions: list[Abstention] = []

    for pattern in patterns:
        metric: str = pattern.metric
        logger.info("Processing pattern for metric '%s'", metric)

        # ---------------------------------------------------------------
        # Step 1 — Extract metric values
        # ---------------------------------------------------------------
        if metric not in df.columns:
            logger.warning(
                "Metric '%s' not found in DataFrame columns; skipping.", metric
            )
            abstentions.append(
                Abstention(
                    metric=metric,
                    reason=f"Metric column '{metric}' not found in dataset",
                )
            )
            continue

        raw_series: pd.Series = df[metric].dropna()
        values_list: list[float] = raw_series.tolist()

        # ---------------------------------------------------------------
        # Step 2 — Evidence validation
        # ---------------------------------------------------------------
        evidence = validate_evidence(raw_series, metric, pattern.percent_change)

        if not evidence.is_sufficient:
            reason = (
                f"Evidence insufficient: {'; '.join(evidence.reasons)}"
            )
            logger.info("Abstaining for '%s': %s", metric, reason)
            abstentions.append(
                Abstention(
                    metric=metric,
                    reason=reason,
                    evidence_result=evidence,
                )
            )
            continue

        # ---------------------------------------------------------------
        # Step 3 — Confidence scoring
        # ---------------------------------------------------------------
        # Use the recent window values for consistency evaluation.
        recent_values: list[float] = (
            values_list[-ROLLING_WINDOW_SIZE:]
            if len(values_list) >= ROLLING_WINDOW_SIZE
            else values_list
        )

        confidence = calculate_confidence(
            sample_size=evidence.sample_size,
            percent_change=pattern.percent_change,
            daily_values=recent_values,
            trend_direction=pattern.trend_direction,
        )

        if confidence.final_confidence < CONFIDENCE_THRESHOLD:
            reason = (
                f"Confidence {confidence.final_confidence:.2f} below "
                f"threshold {CONFIDENCE_THRESHOLD}"
            )
            logger.info("Abstaining for '%s': %s", metric, reason)
            abstentions.append(
                Abstention(
                    metric=metric,
                    reason=reason,
                    evidence_result=evidence,
                )
            )
            continue

        # ---------------------------------------------------------------
        # Step 4 — Build the insight
        # ---------------------------------------------------------------
        metric_label: str = metric.replace("_", " ")
        direction_verb: str = (
            "increased" if pattern.trend_direction == "increasing" else
            "decreased" if pattern.trend_direction == "decreasing" else
            "remained stable"
        )
        window: int = ROLLING_WINDOW_SIZE

        insight_text: str = (
            f"Average daily {metric_label} {direction_verb} by "
            f"{abs(pattern.percent_change):.1f}% over the last {window} "
            f"days (from {pattern.previous_mean:.1f} to "
            f"{pattern.recent_mean:.1f})."
        )

        evidence_text: str = (
            f"Recent {window}-day average: {pattern.recent_mean:.1f}, "
            f"Previous {window}-day average: {pattern.previous_mean:.1f}"
        )

        # Count days following the trend direction in recent values.
        days_in_direction: int = _count_days_in_direction(
            recent_values, pattern.trend_direction
        )

        reasoning_text: str = (
            f"Consistent {pattern.trend_direction} trend observed. "
            f"Linear regression slope: {pattern.slope:.4f}/day "
            f"(R²={pattern.r_squared:.3f}, p={pattern.p_value:.4f}). "
            f"{days_in_direction} of last {len(recent_values)} days showed "
            f"day-over-day {pattern.trend_direction}."
        )

        # ---------------------------------------------------------------
        # Step 5 — Output safety check
        # ---------------------------------------------------------------
        if _contains_forbidden_terms(insight_text):
            logger.error(
                "Insight for '%s' contains forbidden terms; skipping.",
                metric,
            )
            continue

        insight = Insight(
            insight=insight_text,
            metric=metric,
            confidence=confidence.final_confidence,
            confidence_components=confidence,
            evidence=evidence_text,
            reasoning=reasoning_text,
        )
        insights.append(insight)
        logger.info(
            "Generated insight for '%s' with confidence %.2f",
            metric,
            confidence.final_confidence,
        )

    logger.info(
        "Insight generation complete: %d insight(s), %d abstention(s)",
        len(insights),
        len(abstentions),
    )
    return insights, abstentions


# ======================================================================
# Internal helpers
# ======================================================================


def _count_days_in_direction(
    values: list[float], trend_direction: str
) -> int:
    """Count consecutive day-over-day changes matching the trend direction.

    Args:
        values: Ordered daily values.
        trend_direction: ``"increasing"``, ``"decreasing"``, or ``"stable"``.

    Returns:
        Number of transitions that match the expected direction.
    """
    count: int = 0
    for i in range(1, len(values)):
        change: float = values[i] - values[i - 1]
        if trend_direction == "increasing" and change > 0:
            count += 1
        elif trend_direction == "decreasing" and change < 0:
            count += 1
        elif trend_direction == "stable" and abs(change) < 0.05 * abs(
            sum(values) / len(values)
        ):
            count += 1
    return count


def _contains_forbidden_terms(text: str) -> bool:
    """Return ``True`` if *text* contains any term from ``FORBIDDEN_TERMS`` (case-insensitive).

    Args:
        text: The insight text to scan.

    Returns:
        ``True`` if a forbidden term is detected.
    """
    text_lower: str = text.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in text_lower:
            logger.warning("Forbidden term detected: '%s'", term)
            return True
    return False
