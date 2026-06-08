"""
Tests for the anomaly_detector module.

Validates anomaly detection across known-anomaly scenarios, normal-data
baselines, detection-method metadata, explanation quality, chronological
ordering, data-insufficiency guards, and zero-variance edge cases.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from anomaly_detector import detect_anomalies


# =========================================================================
# Known anomaly detection
# =========================================================================


class TestKnownAnomalyDetection:
    """Verify that planted anomalies in the fixture data are flagged."""

    def test_known_anomaly_detected_sleep(self, anomaly_dataframe: pd.DataFrame) -> None:
        """anomaly_dataframe has sleep_hours = 2.5 on day 8 (index 7).

        At least one anomaly should be reported for sleep_hours with an
        observed value close to 2.5.
        """
        anomalies = detect_anomalies(anomaly_dataframe, ["sleep_hours"])

        sleep_anomalies = [a for a in anomalies if a.metric == "sleep_hours"]
        assert len(sleep_anomalies) >= 1, (
            "Expected at least one anomaly for sleep_hours"
        )

        observed_values = [a.observed_value for a in sleep_anomalies]
        assert any(abs(v - 2.5) < 0.1 for v in observed_values), (
            f"Expected an anomaly near 2.5, but observed values were "
            f"{observed_values}"
        )

    def test_known_anomaly_detected_steps(self, anomaly_dataframe: pd.DataFrame) -> None:
        """anomaly_dataframe has steps = 1500 on day 12 (index 11).

        At least one anomaly should be reported for steps with an
        observed value close to 1500.
        """
        anomalies = detect_anomalies(anomaly_dataframe, ["steps"])

        steps_anomalies = [a for a in anomalies if a.metric == "steps"]
        assert len(steps_anomalies) >= 1, (
            "Expected at least one anomaly for steps"
        )

        observed_values = [a.observed_value for a in steps_anomalies]
        assert any(abs(v - 1500) < 100 for v in observed_values), (
            f"Expected an anomaly near 1500, but observed values were "
            f"{observed_values}"
        )


# =========================================================================
# Normal / baseline data
# =========================================================================


class TestNormalDataBaseline:
    """Verify that well-behaved data produces few or no anomalies."""

    def test_normal_data_no_anomalies(self) -> None:
        """A 20-row DataFrame with tightly clustered, normally distributed
        values around mean 50 with std 2 should produce very few (ideally
        zero) anomalies.
        """
        rng = np.random.RandomState(42)
        data = {
            "date": pd.date_range("2025-01-01", periods=20, freq="D"),
            "metric_x": rng.normal(loc=50, scale=2, size=20),
        }
        df = pd.DataFrame(data)

        anomalies = detect_anomalies(df, ["metric_x"])

        # With a tight distribution the z-score and IQR methods should
        # rarely trigger.  We allow at most 2 false positives.
        assert len(anomalies) <= 2, (
            f"Expected at most 2 anomalies for normal data, got "
            f"{len(anomalies)}"
        )

    def test_constant_data_no_anomalies(self, constant_dataframe: pd.DataFrame) -> None:
        """constant_dataframe has all values = 5.0 (zero variance).

        Z-score is skipped when std == 0, and IQR bounds collapse to [5, 5]
        which should not flag the constant values.  No anomalies expected.
        """
        anomalies = detect_anomalies(constant_dataframe, ["metric_a"])

        assert anomalies == [], (
            f"Expected no anomalies for constant data, got {len(anomalies)}"
        )


# =========================================================================
# Anomaly metadata
# =========================================================================


class TestAnomalyMetadata:
    """Validate structural and content properties of returned Anomaly objects."""

    def test_methods_triggered_populated(self, anomaly_dataframe: pd.DataFrame) -> None:
        """Every anomaly must have a non-empty methods_triggered list
        containing only valid method names.
        """
        valid_methods = {"z_score", "iqr", "rolling_deviation"}
        anomalies = detect_anomalies(
            anomaly_dataframe, ["sleep_hours", "steps"]
        )

        assert len(anomalies) > 0, "Need at least one anomaly for this test"

        for anomaly in anomalies:
            assert isinstance(anomaly.methods_triggered, list), (
                "methods_triggered should be a list"
            )
            assert len(anomaly.methods_triggered) > 0, (
                f"methods_triggered should not be empty for {anomaly.metric} "
                f"on {anomaly.date}"
            )
            for method in anomaly.methods_triggered:
                assert method in valid_methods, (
                    f"Unknown method '{method}'; expected one of {valid_methods}"
                )

    def test_explanation_is_human_readable(self, anomaly_dataframe: pd.DataFrame) -> None:
        """The explanation string should reference the metric name and the
        observed value so a reader can immediately understand what happened.
        """
        anomalies = detect_anomalies(anomaly_dataframe, ["sleep_hours"])

        assert len(anomalies) > 0, "Need at least one anomaly for this test"

        for anomaly in anomalies:
            explanation_lower = anomaly.explanation.lower()
            assert anomaly.metric.replace("_", " ") in explanation_lower or anomaly.metric in explanation_lower, (
                f"Explanation should mention metric name '{anomaly.metric}': "
                f"'{anomaly.explanation}'"
            )
            # The observed value (rounded to int in the template) should appear
            assert str(int(round(anomaly.observed_value))) in anomaly.explanation, (
                f"Explanation should mention observed value "
                f"{anomaly.observed_value}: '{anomaly.explanation}'"
            )


# =========================================================================
# Ordering and edge cases
# =========================================================================


class TestOrderingAndEdgeCases:
    """Verify sorting and data-insufficiency behaviour."""

    def test_anomalies_sorted_by_date(self, anomaly_dataframe: pd.DataFrame) -> None:
        """Returned anomalies must be in chronological (ascending) order."""
        anomalies = detect_anomalies(
            anomaly_dataframe, ["sleep_hours", "steps"]
        )

        if len(anomalies) > 1:
            dates = [a.date for a in anomalies]
            assert dates == sorted(dates), (
                f"Anomalies not sorted chronologically: {dates}"
            )

    def test_insufficient_data_skipped(self, small_dataframe: pd.DataFrame) -> None:
        """small_dataframe has only 5 rows, which is below MIN_OBSERVATIONS (7).

        detect_anomalies should skip the metric and return an empty list.
        """
        anomalies = detect_anomalies(small_dataframe, ["steps"])

        assert anomalies == [], (
            f"Expected empty list for {len(small_dataframe)}-row DataFrame, "
            f"but got {len(anomalies)} anomaly/anomalies"
        )
