"""
Tests for the confidence_engine and evidence_validator modules.

Validates confidence sub-scores (sample, trend, consistency, variance),
saturation behaviour, clamping, and the evidence sufficiency gate that
guards insight generation.
"""

from __future__ import annotations

import pytest

from confidence_engine import calculate_confidence
from evidence_validator import validate_evidence
from config import (
    SAMPLE_SIZE_SATURATION,
    TREND_STRENGTH_SATURATION,
    MIN_OBSERVATIONS,
    MIN_COEFFICIENT_OF_VARIATION,
    MIN_TREND_MAGNITUDE_PERCENT,
)


# =========================================================================
# Confidence scoring
# =========================================================================


class TestConfidenceScoring:
    """Verify calculate_confidence under controlled inputs."""

    def test_perfect_confidence_high(self) -> None:
        """Large sample, large percent change, all-increasing daily values,
        and low variance should produce confidence near 1.0.
        """
        result = calculate_confidence(
            sample_size=30,
            percent_change=50.0,
            daily_values=[10, 12, 14, 16, 18, 20, 22],
            trend_direction="increasing",
        )

        assert result.final_confidence >= 0.85, (
            f"Expected high confidence (>=0.85), got {result.final_confidence}"
        )

    def test_low_sample_low_confidence(self) -> None:
        """sample_size=3 should produce sample_score = 3/30 = 0.1."""
        result = calculate_confidence(
            sample_size=3,
            percent_change=25.0,
            daily_values=[10, 12, 14],
            trend_direction="increasing",
        )

        expected_sample = 3 / SAMPLE_SIZE_SATURATION
        assert abs(result.sample_score - expected_sample) < 1e-6, (
            f"Expected sample_score ~{expected_sample}, got {result.sample_score}"
        )

    def test_zero_trend_zero_trend_score(self) -> None:
        """percent_change=0 should yield trend_score=0."""
        result = calculate_confidence(
            sample_size=14,
            percent_change=0.0,
            daily_values=[5, 5, 5, 5, 5, 5, 5],
            trend_direction="stable",
        )

        assert result.trend_score == 0.0, (
            f"Expected trend_score=0.0, got {result.trend_score}"
        )

    def test_saturation_at_max(self) -> None:
        """sample_size=100 → sample_score=1.0 (not >1).
        percent_change=100 → trend_score=1.0 (not >1).
        """
        result = calculate_confidence(
            sample_size=100,
            percent_change=100.0,
            daily_values=[1, 2, 3, 4, 5, 6, 7],
            trend_direction="increasing",
        )

        assert result.sample_score == 1.0, (
            f"sample_score should saturate at 1.0, got {result.sample_score}"
        )
        assert result.trend_score == 1.0, (
            f"trend_score should saturate at 1.0, got {result.trend_score}"
        )

    def test_consistency_all_increasing(self) -> None:
        """daily_values=[1,2,3,4,5,6,7] with direction='increasing'.

        All 6 transitions are positive, so consistency_score should be 1.0.
        """
        result = calculate_confidence(
            sample_size=14,
            percent_change=30.0,
            daily_values=[1, 2, 3, 4, 5, 6, 7],
            trend_direction="increasing",
        )

        assert abs(result.consistency_score - 1.0) < 1e-6, (
            f"Expected consistency_score=1.0, got {result.consistency_score}"
        )

    def test_consistency_mixed(self) -> None:
        """daily_values=[1,3,2,4,3,5,4] with direction='increasing'.

        Transitions: +2, -1, +2, -1, +2, -1 → 3 of 6 are increasing.
        consistency_score should be 0.5.
        """
        result = calculate_confidence(
            sample_size=14,
            percent_change=30.0,
            daily_values=[1, 3, 2, 4, 3, 5, 4],
            trend_direction="increasing",
        )

        assert abs(result.consistency_score - 0.5) < 1e-6, (
            f"Expected consistency_score=0.5, got {result.consistency_score}"
        )

    def test_variance_score_low_cv(self) -> None:
        """Values tightly clustered around 100 → low CV → variance_score near 1.0."""
        result = calculate_confidence(
            sample_size=14,
            percent_change=10.0,
            daily_values=[100, 100.1, 99.9, 100.2, 99.8, 100.1, 100.0],
            trend_direction="stable",
        )

        assert result.variance_score > 0.95, (
            f"Expected variance_score > 0.95 for low-CV data, "
            f"got {result.variance_score}"
        )

    def test_variance_score_high_cv(self) -> None:
        """Values widely spread → high CV → variance_score near 0.0."""
        result = calculate_confidence(
            sample_size=14,
            percent_change=10.0,
            daily_values=[1, 100, 1, 100, 1, 100, 1],
            trend_direction="stable",
        )

        assert result.variance_score < 0.3, (
            f"Expected variance_score < 0.3 for high-CV data, "
            f"got {result.variance_score}"
        )

    def test_final_confidence_clamped(self) -> None:
        """final_confidence should always be within [0, 1] regardless of inputs."""
        # Edge case: extreme inputs
        result = calculate_confidence(
            sample_size=0,
            percent_change=0.0,
            daily_values=[],
            trend_direction="stable",
        )
        assert 0.0 <= result.final_confidence <= 1.0, (
            f"final_confidence {result.final_confidence} out of [0, 1]"
        )

        # Another edge: maximally inflated inputs
        result2 = calculate_confidence(
            sample_size=10_000,
            percent_change=10_000.0,
            daily_values=[1, 2, 3, 4, 5, 6, 7],
            trend_direction="increasing",
        )
        assert 0.0 <= result2.final_confidence <= 1.0, (
            f"final_confidence {result2.final_confidence} out of [0, 1]"
        )

    def test_confidence_components_all_populated(self) -> None:
        """Every field of ConfidenceComponents should be a float."""
        result = calculate_confidence(
            sample_size=14,
            percent_change=20.0,
            daily_values=[5, 6, 7, 8, 9, 10, 11],
            trend_direction="increasing",
        )

        for field_name in (
            "sample_score",
            "trend_score",
            "consistency_score",
            "variance_score",
            "final_confidence",
        ):
            value = getattr(result, field_name)
            assert isinstance(value, float), (
                f"{field_name} should be float, got {type(value)}"
            )


# =========================================================================
# Evidence validation
# =========================================================================


class TestEvidenceValidation:
    """Verify validate_evidence under controlled scenarios."""

    def test_evidence_sufficient_all_pass(self) -> None:
        """30 values with cv > 0.01 and percent_change = 25%.

        All three evidence checks should pass.
        """
        # Linearly increasing values ensure cv > 0.01 and sample >= 7
        values = [float(i) for i in range(10, 40)]  # 30 values: 10..39
        result = validate_evidence(values, "test_metric", percent_change=25.0)

        assert result.is_sufficient is True, (
            f"Expected is_sufficient=True; reasons: {result.reasons}"
        )
        assert result.sample_size == 30
        assert result.has_sufficient_variance is True
        assert result.has_sufficient_signal is True
        assert result.reasons == []

    def test_evidence_insufficient_sample(self) -> None:
        """Only 3 values should fail the sample-size check."""
        values = [10.0, 20.0, 30.0]
        result = validate_evidence(values, "test_metric", percent_change=25.0)

        assert result.is_sufficient is False
        assert result.sample_size == 3
        assert result.sample_size < MIN_OBSERVATIONS, (
            f"sample_size {result.sample_size} should be < {MIN_OBSERVATIONS}"
        )

    def test_evidence_insufficient_variance(self) -> None:
        """Constant values (cv = 0) should fail the variance check."""
        values = [5.0] * 14
        result = validate_evidence(values, "test_metric", percent_change=25.0)

        assert result.has_sufficient_variance is False, (
            "Constant data should fail the variance check"
        )

    def test_evidence_insufficient_signal(self) -> None:
        """percent_change = 1.0% is below MIN_TREND_MAGNITUDE_PERCENT (5%).

        The signal check should fail.
        """
        values = [float(i) for i in range(10, 24)]  # 14 values with variance
        result = validate_evidence(values, "test_metric", percent_change=1.0)

        assert result.has_sufficient_signal is False, (
            f"percent_change=1.0% should fail signal check "
            f"(threshold={MIN_TREND_MAGNITUDE_PERCENT}%)"
        )

    def test_evidence_reasons_populated(self) -> None:
        """When checks fail, the reasons list should contain descriptive strings."""
        # 3 constant values — all 3 checks fail
        values = [5.0, 5.0, 5.0]
        result = validate_evidence(values, "test_metric", percent_change=1.0)

        assert result.is_sufficient is False
        assert len(result.reasons) >= 2, (
            f"Expected at least 2 failure reasons, got {len(result.reasons)}: "
            f"{result.reasons}"
        )
        for reason in result.reasons:
            assert isinstance(reason, str), (
                f"Each reason should be a string, got {type(reason)}"
            )
            assert len(reason) > 10, (
                f"Reason '{reason}' is too short to be descriptive"
            )
