"""
Tests for the pattern_detector module.

Validates trend detection across multiple behavioural scenarios,
regression statistics population, supporting statistics structure,
data-insufficiency guards, and multi-metric batch processing.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pattern_detector import detect_patterns
from config import TREND_THRESHOLD_PERCENT, MIN_OBSERVATIONS


# =========================================================================
# Individual trend direction tests
# =========================================================================


class TestTrendDirectionDetection:
    """Verify that detect_patterns correctly classifies trend directions."""

    def test_declining_trend_detected(self, sample_dataframe: pd.DataFrame) -> None:
        """Steps in sample_dataframe decline from ~8000 to ~5000.

        The function should classify the trend as 'decreasing' with a
        negative percent change exceeding the threshold, and a negative slope.
        """
        results = detect_patterns(sample_dataframe, ["steps"])

        assert len(results) == 1, "Expected exactly one TrendResult for 'steps'"
        trend = results[0]

        assert trend.metric == "steps"
        assert trend.trend_direction == "decreasing", (
            f"Expected 'decreasing' but got '{trend.trend_direction}'"
        )
        assert trend.percent_change < -TREND_THRESHOLD_PERCENT, (
            f"Percent change {trend.percent_change} should be below "
            f"-{TREND_THRESHOLD_PERCENT}%"
        )
        assert trend.slope < 0, (
            f"Slope {trend.slope} should be negative for declining data"
        )
        assert trend.r_squared > 0, (
            f"R-squared {trend.r_squared} should be positive"
        )

    def test_increasing_trend_detected(self, sample_dataframe: pd.DataFrame) -> None:
        """Screen time in sample_dataframe increases from ~180 to ~320.

        The function should classify the trend as 'increasing' with a
        positive percent change exceeding the threshold and a positive slope.
        """
        results = detect_patterns(sample_dataframe, ["screen_time_minutes"])

        assert len(results) == 1, "Expected exactly one TrendResult for 'screen_time_minutes'"
        trend = results[0]

        assert trend.metric == "screen_time_minutes"
        assert trend.trend_direction == "increasing", (
            f"Expected 'increasing' but got '{trend.trend_direction}'"
        )
        assert trend.percent_change > TREND_THRESHOLD_PERCENT, (
            f"Percent change {trend.percent_change} should exceed "
            f"+{TREND_THRESHOLD_PERCENT}%"
        )
        assert trend.slope > 0, (
            f"Slope {trend.slope} should be positive for increasing data"
        )

    def test_stable_trend_detected(self, sample_dataframe: pd.DataFrame) -> None:
        """Sleep hours in sample_dataframe hover around 7.0 with tiny variation.

        The function should classify the trend as 'stable' with percent
        change within the ±threshold range.
        """
        results = detect_patterns(sample_dataframe, ["sleep_hours"])

        assert len(results) == 1, "Expected exactly one TrendResult for 'sleep_hours'"
        trend = results[0]

        assert trend.metric == "sleep_hours"
        assert trend.trend_direction == "stable", (
            f"Expected 'stable' but got '{trend.trend_direction}'"
        )
        assert -TREND_THRESHOLD_PERCENT <= trend.percent_change <= TREND_THRESHOLD_PERCENT, (
            f"Percent change {trend.percent_change} should be within "
            f"±{TREND_THRESHOLD_PERCENT}%"
        )


# =========================================================================
# Regression statistics
# =========================================================================


class TestRegressionStatistics:
    """Verify that linear regression outputs are populated and reasonable."""

    def test_regression_provides_statistics(self, sample_dataframe: pd.DataFrame) -> None:
        """All regression fields (slope, r_squared, p_value) should be
        present and numeric for every detected trend."""
        results = detect_patterns(
            sample_dataframe,
            ["steps", "screen_time_minutes", "sleep_hours"],
        )

        for trend in results:
            assert isinstance(trend.slope, float), (
                f"slope should be float, got {type(trend.slope)}"
            )
            assert isinstance(trend.r_squared, float), (
                f"r_squared should be float, got {type(trend.r_squared)}"
            )
            assert isinstance(trend.p_value, float), (
                f"p_value should be float, got {type(trend.p_value)}"
            )
            # R² is always in [0, 1]
            assert 0.0 <= trend.r_squared <= 1.0, (
                f"R² {trend.r_squared} should be in [0, 1]"
            )
            # p-value is always in [0, 1]
            assert 0.0 <= trend.p_value <= 1.0, (
                f"p-value {trend.p_value} should be in [0, 1]"
            )

    def test_supporting_statistics_keys(self, sample_dataframe: pd.DataFrame) -> None:
        """supporting_statistics dict must contain exactly the expected keys."""
        expected_keys = {
            "window_comparison_pct",
            "regression_slope",
            "regression_significant",
            "methods_agree",
            "days_in_trend_direction",
        }

        results = detect_patterns(sample_dataframe, ["steps"])
        assert len(results) == 1

        actual_keys = set(results[0].supporting_statistics.keys())
        assert actual_keys == expected_keys, (
            f"Expected keys {expected_keys}, got {actual_keys}"
        )


# =========================================================================
# Edge cases and data-insufficiency guards
# =========================================================================


class TestEdgeCases:
    """Verify behaviour under boundary and degenerate inputs."""

    def test_insufficient_data_skipped(self, small_dataframe: pd.DataFrame) -> None:
        """small_dataframe has 5 rows, which is below MIN_OBSERVATIONS (7).

        detect_patterns should skip the metric and return an empty list.
        """
        results = detect_patterns(small_dataframe, ["steps"])

        assert results == [], (
            f"Expected empty list for {len(small_dataframe)}-row DataFrame, "
            f"but got {len(results)} result(s)"
        )

    def test_empty_metric_list_returns_empty(self, sample_dataframe: pd.DataFrame) -> None:
        """Passing an empty metric_columns list should return an empty list."""
        results = detect_patterns(sample_dataframe, [])

        assert results == [], (
            f"Expected empty list for empty metric_columns, "
            f"but got {len(results)} result(s)"
        )

    def test_multiple_metrics_detected(self, sample_dataframe: pd.DataFrame) -> None:
        """When all 3 metrics are requested, exactly 3 TrendResults should be
        returned — one per metric."""
        metrics = ["steps", "screen_time_minutes", "sleep_hours"]
        results = detect_patterns(sample_dataframe, metrics)

        assert len(results) == 3, (
            f"Expected 3 TrendResults, got {len(results)}"
        )

        detected_metrics = {r.metric for r in results}
        assert detected_metrics == set(metrics), (
            f"Expected metrics {set(metrics)}, got {detected_metrics}"
        )
