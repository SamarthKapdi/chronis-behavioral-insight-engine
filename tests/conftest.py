"""
Pytest configuration and shared fixtures for the Behavioral Insight Engine.

Adds the ``src/`` directory to ``sys.path`` so that test modules can
import source modules directly (e.g., ``from data_loader import ...``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Path setup — allow imports from src/
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a minimal 14-day DataFrame for testing.

    Contains clear patterns:
    - steps: declining from ~8000 to ~5000
    - screen_time_minutes: increasing from ~180 to ~320
    - sleep_hours: stable around 7.0
    """
    data = {
        "date": pd.date_range("2025-01-01", periods=14, freq="D"),
        "sleep_hours": [
            7.2, 7.0, 7.4, 6.9, 7.3, 7.1, 7.5,
            7.0, 7.2, 7.3, 6.8, 7.1, 7.4, 7.0,
        ],
        "steps": [
            8200, 8000, 8100, 7800, 7900, 8050, 7950,
            6500, 6200, 6000, 5800, 5500, 5200, 5000,
        ],
        "screen_time_minutes": [
            180, 175, 190, 185, 195, 170, 188,
            240, 260, 275, 290, 300, 310, 320,
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def small_dataframe() -> pd.DataFrame:
    """Create a very small DataFrame (5 rows) for testing insufficient data."""
    data = {
        "date": pd.date_range("2025-01-01", periods=5, freq="D"),
        "sleep_hours": [7.0, 7.2, 7.1, 7.3, 7.0],
        "steps": [8000, 8100, 7900, 8200, 8000],
    }
    return pd.DataFrame(data)


@pytest.fixture
def anomaly_dataframe() -> pd.DataFrame:
    """Create a DataFrame with known anomalies for testing.

    Known anomalies:
    - Day 8: sleep_hours = 2.5 (very low)
    - Day 12: steps = 1500 (very low)
    """
    data = {
        "date": pd.date_range("2025-01-01", periods=14, freq="D"),
        "sleep_hours": [
            7.2, 7.0, 7.4, 6.9, 7.3, 7.1, 7.5,
            2.5, 7.2, 7.3, 6.8, 7.1, 7.4, 7.0,
        ],
        "steps": [
            8200, 8000, 8100, 7800, 7900, 8050, 7950,
            7800, 8000, 7900, 7850, 1500, 8100, 8000,
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def constant_dataframe() -> pd.DataFrame:
    """Create a DataFrame with zero variance for edge-case testing."""
    data = {
        "date": pd.date_range("2025-01-01", periods=14, freq="D"),
        "metric_a": [5.0] * 14,
    }
    return pd.DataFrame(data)


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return _PROJECT_ROOT
