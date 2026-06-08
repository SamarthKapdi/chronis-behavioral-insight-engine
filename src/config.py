"""
Configuration constants for the Behavioral Insight Engine.

All tunable parameters are centralized here to avoid magic numbers
scattered throughout the codebase and to simplify experimentation.
"""

# ---------------------------------------------------------------------------
# Pattern Detection
# ---------------------------------------------------------------------------

ROLLING_WINDOW_SIZE: int = 7
"""Number of days in each comparison window (recent vs. previous)."""

TREND_THRESHOLD_PERCENT: float = 10.0
"""Minimum |percent change| to classify a trend as increasing or decreasing."""

REGRESSION_P_VALUE_THRESHOLD: float = 0.05
"""Maximum p-value for a regression slope to be considered significant."""

# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------

ZSCORE_THRESHOLD: float = 2.5
"""Minimum |z-score| to flag an observation as anomalous."""

IQR_MULTIPLIER: float = 1.5
"""Multiplier for IQR to define the expected range."""

ROLLING_DEVIATION_WINDOW: int = 7
"""Window size for rolling mean/std used in rolling deviation detection."""

ROLLING_DEVIATION_THRESHOLD: float = 2.0
"""Number of rolling standard deviations beyond which a value is anomalous."""

# ---------------------------------------------------------------------------
# Evidence Sufficiency
# ---------------------------------------------------------------------------

MIN_OBSERVATIONS: int = 7
"""Minimum number of non-missing observations required for analysis."""

MIN_COEFFICIENT_OF_VARIATION: float = 0.01
"""Minimum coefficient of variation to confirm meaningful variance exists."""

MIN_TREND_MAGNITUDE_PERCENT: float = 5.0
"""Minimum |percent change| to consider a signal worth reporting."""

# ---------------------------------------------------------------------------
# Confidence Scoring
# ---------------------------------------------------------------------------

CONFIDENCE_THRESHOLD: float = 0.60
"""Minimum confidence score to emit an insight (below this → abstain)."""

WEIGHT_SAMPLE_SIZE: float = 0.25
"""Weight for sample-size component in confidence formula."""

WEIGHT_TREND_STRENGTH: float = 0.35
"""Weight for trend-strength component in confidence formula."""

WEIGHT_CONSISTENCY: float = 0.25
"""Weight for consistency component in confidence formula."""

WEIGHT_VARIANCE: float = 0.15
"""Weight for variance component in confidence formula."""

SAMPLE_SIZE_SATURATION: int = 30
"""Sample size at which sample_score saturates to 1.0."""

TREND_STRENGTH_SATURATION: float = 50.0
"""Percent change magnitude at which trend_score saturates to 1.0."""

# ---------------------------------------------------------------------------
# Output Safety
# ---------------------------------------------------------------------------

FORBIDDEN_TERMS: list[str] = [
    "lazy",
    "depressed",
    "depression",
    "addicted",
    "addiction",
    "undisciplined",
    "anxious",
    "anxiety",
    "mental health",
    "diagnosis",
    "disorder",
    "therapy",
    "medication",
    "personality",
    "character flaw",
    "unhealthy person",
]
"""Terms that must never appear in generated insights or reports."""

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_DATA_PATH: str = "data/behavioral_data.csv"
"""Default path to the input CSV file, relative to repository root."""

DEFAULT_OUTPUT_DIR: str = "outputs"
"""Default directory for generated output files."""
