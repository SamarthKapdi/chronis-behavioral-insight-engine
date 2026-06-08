"""
Tests for the data loader and feature engineering modules.

Verifies schema discovery, CSV validation, rolling feature calculation,
excessive missing values detection, and custom exception handling.
"""

from __future__ import annotations

import os
import pandas as pd
import pytest

from exceptions import DataLoadError, SchemaValidationError, InsufficientDataError
from data_loader import load_behavioral_data, _detect_date_column, _detect_metric_columns
from feature_engineering import compute_rolling_stats, get_metric_series


def test_detect_date_column_heuristics() -> None:
    # 1. By name convention
    df1 = pd.DataFrame({"obs_date": ["2025-01-01", "2025-01-02"], "value": [10, 20]})
    assert _detect_date_column(df1) == "obs_date"

    # 2. By parseability
    df2 = pd.DataFrame({"time": ["2025-01-01", "2025-01-02"], "value": [10, 20]})
    assert _detect_date_column(df2) == "time"

    # 3. No date column
    df3 = pd.DataFrame({"value1": [10, 20], "value2": [30, 40]})
    with pytest.raises(SchemaValidationError, match="No date column detected"):
        _detect_date_column(df3)


def test_detect_metric_columns() -> None:
    df = pd.DataFrame({"date": ["2025-01-01"], "metric1": [10], "metric2": [20.5], "not_a_metric": ["text"]})
    metrics = _detect_metric_columns(df, "date")
    assert metrics == ["metric1", "metric2"]

    df_no_metrics = pd.DataFrame({"date": ["2025-01-01"], "not_a_metric": ["text"]})
    with pytest.raises(SchemaValidationError, match="No numeric metric columns found"):
        _detect_metric_columns(df_no_metrics, "date")


def test_load_behavioral_data_success(tmp_path) -> None:
    csv_path = tmp_path / "test_data.csv"
    csv_content = (
        "date,steps,sleep_hours,screen_time\n"
        "2025-01-01,8000,7.2,180\n"
        "2025-01-02,7500,6.8,200\n"
        "2025-01-03,8200,7.5,150\n"
        "2025-01-04,7800,7.0,190\n"
        "2025-01-05,8100,7.3,170\n"
        "2025-01-06,8300,7.8,210\n"
        "2025-01-07,7900,7.1,185\n"
    )
    csv_path.write_text(csv_content)

    df, schema, group_col = load_behavioral_data(str(csv_path))
    assert schema.date_column == "date"
    assert schema.metric_columns == ["screen_time", "sleep_hours", "steps"]
    assert schema.row_count == 7
    assert schema.date_range == ("2025-01-01", "2025-01-07")
    assert schema.missing_value_counts == {"date": 0, "screen_time": 0, "sleep_hours": 0, "steps": 0}
    assert len(df) == 7


def test_load_behavioral_data_missing_file() -> None:
    with pytest.raises(DataLoadError, match="File not found"):
        load_behavioral_data("non_existent_file_xyz.csv")


def test_load_behavioral_data_empty_file(tmp_path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("")
    with pytest.raises(DataLoadError, match="empty"):
        load_behavioral_data(str(csv_path))


def test_load_behavioral_data_too_few_rows(tmp_path) -> None:
    csv_path = tmp_path / "short.csv"
    csv_content = (
        "date,steps\n"
        "2025-01-01,8000\n"
        "2025-01-02,7500\n"
    )
    csv_path.write_text(csv_content)
    with pytest.raises(SchemaValidationError, match="at least 7 are required"):
        load_behavioral_data(str(csv_path))


def test_compute_rolling_stats_success(sample_dataframe) -> None:
    # sample_dataframe has 14 rows, window_size=7 requires 14 rows, so it fits perfectly.
    results = compute_rolling_stats(sample_dataframe, ["steps", "screen_time_minutes"], window_size=7)
    assert "steps" in results
    assert "screen_time_minutes" in results

    stats = results["steps"]
    assert len(stats.recent_values) == 7
    assert len(stats.previous_values) == 7
    assert stats.recent_mean < stats.previous_mean


def test_compute_rolling_stats_insufficient_data(small_dataframe) -> None:
    with pytest.raises(InsufficientDataError, match="at least 14 are required"):
        compute_rolling_stats(small_dataframe, ["sleep_hours"], window_size=7)


def test_compute_rolling_stats_excessive_nans(sample_dataframe) -> None:
    # Inject more than 50% NaNs (e.g. 4 NaNs out of 7) in the recent window of sleep_hours
    df_nans = sample_dataframe.copy()
    df_nans.loc[10:13, "sleep_hours"] = None

    results = compute_rolling_stats(df_nans, ["sleep_hours"], window_size=7)
    # sleep_hours should be skipped
    assert "sleep_hours" not in results


def test_get_metric_series(sample_dataframe) -> None:
    df = sample_dataframe.copy()
    df.loc[3, "steps"] = None

    series = get_metric_series(df, "steps")
    assert len(series) == 13
    assert 3 not in series.index

    with pytest.raises(KeyError, match="not found"):
        get_metric_series(df, "non_existent")
