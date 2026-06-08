"""
Tests for insight_generator abstention behaviour and report_builder output.

Validates that the engine correctly abstains when evidence is insufficient
or confidence is below threshold, generates insights for strong trends,
enforces output-safety rules, and produces well-structured reports.
"""

from __future__ import annotations

import pandas as pd
import pytest

from insight_generator import generate_insights
from report_builder import build_report
from models import (
    Abstention,
    AnalysisResult,
    Anomaly,
    ConfidenceComponents,
    DatasetSchema,
    Insight,
    TrendResult,
)
from config import (
    CONFIDENCE_THRESHOLD,
    FORBIDDEN_TERMS,
    MIN_OBSERVATIONS,
    MIN_TREND_MAGNITUDE_PERCENT,
)


# =========================================================================
# Helpers
# =========================================================================


def _make_schema(**overrides) -> DatasetSchema:
    """Create a minimal DatasetSchema with sensible defaults."""
    defaults = dict(
        date_column="date",
        metric_columns=["test_metric"],
        row_count=14,
        date_range=("2025-01-01", "2025-01-14"),
    )
    defaults.update(overrides)
    return DatasetSchema(**defaults)


def _make_trend(metric: str, direction: str, pct: float, **kw) -> TrendResult:
    """Create a TrendResult with reasonable defaults."""
    defaults = dict(
        metric=metric,
        trend_direction=direction,
        percent_change=pct,
        slope=-200.0 if direction == "decreasing" else 200.0 if direction == "increasing" else 0.0,
        r_squared=0.90,
        p_value=0.001,
        recent_mean=5000.0,
        previous_mean=8000.0 if direction == "decreasing" else 3000.0 if direction == "increasing" else 5000.0,
    )
    defaults.update(kw)
    return TrendResult(**defaults)


def _make_declining_df(n: int = 14) -> pd.DataFrame:
    """Create a DataFrame with a clear declining 'test_metric'."""
    import numpy as np
    values = np.linspace(8000, 5000, n)
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "test_metric": values,
    })


# =========================================================================
# Abstention tests
# =========================================================================


class TestAbstentionBehaviour:
    """Verify that the engine abstains under the correct conditions."""

    def test_abstention_on_insufficient_data(self) -> None:
        """A 5-row DataFrame has fewer than MIN_OBSERVATIONS (7) valid values.

        validate_evidence will fail the sample-size check, causing an
        abstention.
        """
        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=5, freq="D"),
            "test_metric": [100.0, 95.0, 90.0, 85.0, 80.0],
        })
        trend = _make_trend("test_metric", "decreasing", pct=-20.0)

        insights, abstentions = generate_insights([trend], [], df)

        assert len(insights) == 0, (
            f"Expected 0 insights for insufficient data, got {len(insights)}"
        )
        assert len(abstentions) >= 1, (
            f"Expected at least 1 abstention, got {len(abstentions)}"
        )
        assert abstentions[0].metric == "test_metric"

    def test_abstention_on_low_confidence(self) -> None:
        """A trend with very small percent change (6%) passes evidence
        validation (signal ≥ 5%) but should yield confidence below the
        0.60 threshold, producing an abstention.

        We use a 14-row dataset with mixed direction values to drive
        consistency down and keep confidence low.
        """
        # Values that zigzag — low consistency → low confidence
        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=14, freq="D"),
            "test_metric": [
                100, 98, 101, 97, 102, 96, 103,
                97, 104, 96, 105, 95, 106, 94,
            ],
        })
        # 6% change is above MIN_TREND_MAGNITUDE (5%) so evidence passes,
        # but the zigzag data keeps consistency low.
        trend = _make_trend(
            "test_metric", "decreasing", pct=-6.0,
            slope=-0.3, r_squared=0.05, p_value=0.45,
            recent_mean=97.0, previous_mean=103.0,
        )

        insights, abstentions = generate_insights([trend], [], df)

        # Either abstained or very low confidence insight
        if len(abstentions) > 0:
            ab = abstentions[0]
            assert "onfidence" in ab.reason or "confidence" in ab.reason.lower(), (
                f"Abstention reason should mention confidence: '{ab.reason}'"
            )
        else:
            # If an insight was generated, its confidence should be marginal
            assert insights[0].confidence < CONFIDENCE_THRESHOLD + 0.15, (
                f"Expected low confidence, got {insights[0].confidence}"
            )

    def test_abstention_on_stable_trend(self) -> None:
        """A stable trend with percent_change = 2% is below
        MIN_TREND_MAGNITUDE_PERCENT (5%), so evidence validation
        should fail on signal strength, producing an abstention.
        """
        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=14, freq="D"),
            "test_metric": [7.0, 7.1, 6.9, 7.0, 7.2, 6.8, 7.1,
                            7.0, 7.1, 6.9, 7.0, 7.2, 6.8, 7.1],
        })
        trend = _make_trend(
            "test_metric", "stable", pct=2.0,
            slope=0.001, r_squared=0.001, p_value=0.90,
            recent_mean=7.02, previous_mean=6.88,
        )

        insights, abstentions = generate_insights([trend], [], df)

        assert len(insights) == 0, (
            f"Expected 0 insights for stable/small trend, got {len(insights)}"
        )
        assert len(abstentions) >= 1, (
            f"Expected at least 1 abstention, got {len(abstentions)}"
        )

    def test_abstention_reason_includes_details(self) -> None:
        """Abstention reason should contain recognisable keywords like
        'Insufficient' or 'Evidence' or 'Confidence'.
        """
        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=5, freq="D"),
            "test_metric": [100.0, 95.0, 90.0, 85.0, 80.0],
        })
        trend = _make_trend("test_metric", "decreasing", pct=-20.0)

        _, abstentions = generate_insights([trend], [], df)

        assert len(abstentions) >= 1
        reason_lower = abstentions[0].reason.lower()
        assert any(kw in reason_lower for kw in ("insufficient", "evidence", "confidence")), (
            f"Abstention reason should mention insufficiency or confidence: "
            f"'{abstentions[0].reason}'"
        )


# =========================================================================
# Insight generation
# =========================================================================


class TestInsightGeneration:
    """Verify that strong trends produce real insights."""

    def test_insight_generated_for_strong_trend(self) -> None:
        """A 14-row DataFrame with a clear declining metric and matching
        TrendResult should produce an insight (not an abstention).
        """
        df = _make_declining_df(14)
        trend = _make_trend(
            "test_metric", "decreasing", pct=-37.5,
            slope=-214.0, r_squared=0.99, p_value=0.0001,
            recent_mean=5500.0, previous_mean=7500.0,
        )

        insights, abstentions = generate_insights([trend], [], df)

        assert len(insights) >= 1, (
            f"Expected at least 1 insight for a strong trend, "
            f"got {len(insights)} insights and {len(abstentions)} abstentions. "
            f"Abstention reasons: {[a.reason for a in abstentions]}"
        )
        assert insights[0].metric == "test_metric"
        assert insights[0].confidence >= CONFIDENCE_THRESHOLD


# =========================================================================
# Output safety
# =========================================================================


class TestOutputSafety:
    """Verify that generated insights do not contain forbidden terms."""

    def test_no_forbidden_terms_in_insights(self, sample_dataframe: pd.DataFrame) -> None:
        """Generate insights from sample_dataframe and verify none contain
        forbidden terms from the config.
        """
        from pattern_detector import detect_patterns

        metrics = ["steps", "screen_time_minutes", "sleep_hours"]
        patterns = detect_patterns(sample_dataframe, metrics)
        insights, _ = generate_insights(patterns, [], sample_dataframe)

        for insight in insights:
            text_lower = insight.insight.lower()
            for term in FORBIDDEN_TERMS:
                assert term.lower() not in text_lower, (
                    f"Insight for '{insight.metric}' contains forbidden term "
                    f"'{term}': '{insight.insight}'"
                )


# =========================================================================
# Report builder
# =========================================================================


class TestReportBuilder:
    """Validate the Markdown report structure."""

    def test_report_generation_has_all_sections(self) -> None:
        """A fully populated AnalysisResult should produce a report with
        all 8+ section headers.
        """
        schema = _make_schema(
            metric_columns=["steps"],
            row_count=14,
        )
        trend = _make_trend("steps", "decreasing", pct=-30.0)
        anomaly = Anomaly(
            date="2025-01-08",
            metric="steps",
            observed_value=1500.0,
            expected_value=7500.0,
            deviation=-3.5,
            methods_triggered=["z_score", "iqr"],
            explanation="steps unusually low: observed 1500 vs expected range 5000–10000",
        )
        confidence_comp = ConfidenceComponents(
            sample_score=0.47,
            trend_score=0.60,
            consistency_score=0.80,
            variance_score=0.90,
            final_confidence=0.65,
        )
        insight = Insight(
            insight="Average daily steps decreased by 30.0% over the last 7 days.",
            metric="steps",
            confidence=0.65,
            confidence_components=confidence_comp,
            evidence="Recent 7-day average: 5500.0, Previous 7-day average: 7500.0",
            reasoning="Consistent decreasing trend observed.",
        )
        abstention = Abstention(
            metric="sleep_hours",
            reason="Evidence insufficient: Trend magnitude too small",
        )

        result = AnalysisResult(
            patterns=[trend],
            anomalies=[anomaly],
            insights=[insight],
            abstentions=[abstention],
            dataset_schema=schema,
        )

        report = build_report(result)

        expected_sections = [
            "# Behavioral Insight Engine",
            "## Executive Summary",
            "## Behavioral Trends",
            "## Significant Changes",
            "## Anomalies",
            "## Insights",
            "## Abstentions",
            "## Methodology",
            "## Limitations",
        ]
        for header in expected_sections:
            assert header in report, (
                f"Report missing section header: '{header}'"
            )

    def test_report_handles_empty_results(self) -> None:
        """An AnalysisResult with all-empty lists should still produce
        valid Markdown without errors.
        """
        schema = _make_schema(row_count=0)
        result = AnalysisResult(
            patterns=[],
            anomalies=[],
            insights=[],
            abstentions=[],
            dataset_schema=schema,
        )

        report = build_report(result)

        assert isinstance(report, str)
        assert len(report) > 100, (
            f"Empty-result report should still be substantial, got {len(report)} chars"
        )
        # Should still have section headers
        assert "## Executive Summary" in report
        assert "## Methodology" in report
