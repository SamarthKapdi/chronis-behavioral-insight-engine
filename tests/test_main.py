"""
Tests for the main pipeline orchestrator.

Verifies logging setup, CLI argument parsing, file writing helpers,
and full end-to-end pipeline execution with clean error handling.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import pytest

import main
from exceptions import DataLoadError


def test_setup_logging() -> None:
    # Call to ensure it executes without crashing
    main._setup_logging()


def test_resolve_data_path_default(monkeypatch) -> None:
    # Mock sys.argv to have no arguments
    monkeypatch.setattr(sys, "argv", ["src/main.py"])
    path = main._resolve_data_path()
    assert path.name == "behavioral_data.csv"
    assert path.parent.name == "data"


def test_resolve_data_path_custom_relative(monkeypatch) -> None:
    # Mock sys.argv with a custom relative path
    monkeypatch.setattr(sys, "argv", ["src/main.py", "custom/data.csv"])
    path = main._resolve_data_path()
    assert path.name == "data.csv"
    assert path.parent.name == "custom"


def test_resolve_data_path_custom_absolute(monkeypatch, tmp_path) -> None:
    abs_path = tmp_path / "my_abs_data.csv"
    # Mock sys.argv with a custom absolute path
    monkeypatch.setattr(sys, "argv", ["src/main.py", str(abs_path)])
    path = main._resolve_data_path()
    assert path == abs_path


def test_write_json(tmp_path) -> None:
    target_file = tmp_path / "test_out.json"
    data = [{"name": "steps", "value": 8000}]
    main._write_json(data, target_file)

    assert target_file.exists()
    with open(target_file, "r", encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded == data


def test_main_pipeline_success(monkeypatch, tmp_path) -> None:
    # Create a dummy data file that has sufficient rows
    data_csv = tmp_path / "dummy_data.csv"
    csv_content = (
        "date,sleep_hours,screen_time_minutes,steps,active_minutes,resting_heart_rate,mood_score,productivity_score\n"
        "2025-01-01,7.4,175,8200,48,64,7,8\n"
        "2025-01-02,7.1,190,7850,42,65,7,7\n"
        "2025-01-03,7.6,168,8400,52,63,8,8\n"
        "2025-01-04,6.9,195,7900,44,66,7,7\n"
        "2025-01-05,7.3,185,8100,46,64,7,8\n"
        "2025-01-06,7.8,200,8350,50,62,8,7\n"
        "2025-01-07,7.2,178,7950,43,65,7,8\n"
        "2025-01-08,7.0,210,7600,40,63,7,7\n"
        "2025-01-09,7.5,225,7400,38,66,6,7\n"
        "2025-01-10,7.3,215,7200,42,64,7,8\n"
        "2025-01-11,6.8,240,7000,36,67,6,7\n"
        "2025-01-12,7.4,230,7350,39,63,7,7\n"
        "2025-01-13,7.1,250,6800,34,65,6,6\n"
        "2025-01-14,7.6,235,7100,37,64,7,7\n"
    )
    data_csv.write_text(csv_content)

    # Mock _resolve_data_path to return our dummy csv
    monkeypatch.setattr(main, "_resolve_data_path", lambda: data_csv)

    # Mock DEFAULT_OUTPUT_DIR to write directly to our temp directory
    out_dir = tmp_path / "outputs"
    monkeypatch.setattr(main, "DEFAULT_OUTPUT_DIR", str(out_dir))

    # Run main pipeline
    main.main()

    # Verify all output files are generated
    assert (out_dir / "patterns.json").exists()
    assert (out_dir / "anomalies.json").exists()
    assert (out_dir / "insights.json").exists()
    assert (out_dir / "abstentions.json").exists()
    assert (out_dir / "report.md").exists()


def test_main_pipeline_failure(monkeypatch, tmp_path) -> None:
    # Mock _resolve_data_path to return a non-existent file path
    non_existent = tmp_path / "does_not_exist.csv"
    monkeypatch.setattr(main, "_resolve_data_path", lambda: non_existent)

    # Verify that the pipeline exits with code 1 upon catching BehavioralInsightError
    with pytest.raises(SystemExit) as excinfo:
        main.main()
    assert excinfo.value.code == 1
