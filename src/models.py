"""
Shared data models for the Behavioral Insight Engine.

All dataclasses used across the pipeline are defined here to ensure
a single source of truth for data structures and enable consistent
serialization throughout the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DatasetSchema:
    """Describes the discovered schema of the input dataset.

    Attributes:
        date_column: Name of the column containing dates.
        metric_columns: Names of all numeric behavioral metric columns.
        row_count: Total number of rows in the dataset.
        date_range: Tuple of (earliest_date, latest_date) as ISO strings.
        missing_value_counts: Count of missing values per column.
        group_column: Name of the grouping column (e.g. 'user_id'), or None.
    """

    date_column: str
    metric_columns: list[str]
    row_count: int
    date_range: tuple[str, str]
    missing_value_counts: dict[str, int] = field(default_factory=dict)
    group_column: str | None = None


@dataclass
class RollingStats:
    """Rolling window statistics for a single metric.

    Compares a recent window against a previous window to enable
    trend detection via window comparison.

    Attributes:
        metric: Name of the behavioral metric.
        recent_values: Raw values from the recent window.
        previous_values: Raw values from the previous window.
        recent_mean: Mean of the recent window.
        previous_mean: Mean of the previous window.
        recent_std: Standard deviation of the recent window.
        previous_std: Standard deviation of the previous window.
    """

    metric: str
    recent_values: list[float]
    previous_values: list[float]
    recent_mean: float
    previous_mean: float
    recent_std: float
    previous_std: float


@dataclass
class TrendResult:
    """Result of trend analysis combining window comparison and linear regression.

    Each trend result captures both the window-based percent change and the
    regression-based slope, providing two complementary views of the trend.

    Attributes:
        metric: Name of the behavioral metric.
        trend_direction: One of ``"increasing"``, ``"decreasing"``, or ``"stable"``.
        percent_change: Percent change from previous to recent window.
        slope: Linear regression slope (units per day).
        r_squared: Coefficient of determination from linear regression.
        p_value: p-value of the regression slope.
        recent_mean: Mean of the recent window.
        previous_mean: Mean of the previous window.
        supporting_statistics: Additional context such as days_in_direction.
    """

    metric: str
    trend_direction: str
    percent_change: float
    slope: float
    r_squared: float
    p_value: float
    recent_mean: float
    previous_mean: float
    supporting_statistics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Anomaly:
    """A detected anomaly in behavioral data.

    Anomalies are flagged when at least one statistical method
    (Z-score, IQR, or rolling deviation) identifies an observation
    as significantly outside expected bounds.

    Attributes:
        date: ISO-format date string of the anomalous observation.
        metric: Name of the behavioral metric.
        observed_value: The actual observed value.
        expected_value: The expected value (e.g., mean or median).
        deviation: How far the observation deviates from expected (in std devs or IQR units).
        methods_triggered: Which detection methods flagged this anomaly.
        explanation: Human-readable explanation of why this was flagged.
    """

    date: str
    metric: str
    observed_value: float
    expected_value: float
    deviation: float
    methods_triggered: list[str]
    explanation: str


@dataclass
class EvidenceResult:
    """Result of evidence sufficiency validation for a metric.

    Before generating insights, each metric's data is validated to ensure
    there is sufficient evidence to make reliable claims.

    Attributes:
        metric: Name of the behavioral metric.
        is_sufficient: Whether evidence passes all sufficiency checks.
        sample_size: Number of valid (non-NaN) observations.
        has_sufficient_variance: Whether the data has meaningful variation.
        has_sufficient_signal: Whether the trend signal is strong enough.
        reasons: Explanations for any sufficiency failures.
    """

    metric: str
    is_sufficient: bool
    sample_size: int
    has_sufficient_variance: bool
    has_sufficient_signal: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class ConfidenceComponents:
    """Breakdown of confidence score into explainable components.

    Each component contributes to the final weighted confidence score,
    making the scoring fully transparent and auditable.

    Weights:
        sample_score   × 0.25
        trend_score    × 0.35
        consistency    × 0.25
        variance_score × 0.15

    Attributes:
        sample_score: Normalized sample size (0–1). Saturates at 30 days.
        trend_score: Normalized trend magnitude (0–1). Based on |percent_change|.
        consistency_score: Fraction of days following trend direction (0–1).
        variance_score: Stability measure (0–1). Lower CV → higher score.
        final_confidence: Weighted combination, clamped to [0, 1].
    """

    sample_score: float
    trend_score: float
    consistency_score: float
    variance_score: float
    final_confidence: float


@dataclass
class Insight:
    """A generated behavioral insight backed by evidence.

    Insights are only generated when evidence is sufficient and
    confidence exceeds the configured threshold (default 0.60).

    Attributes:
        insight: Human-readable insight statement.
        metric: Name of the behavioral metric.
        confidence: Final confidence score (0–1).
        confidence_components: Full breakdown of confidence factors.
        evidence: Specific data evidence supporting the insight.
        reasoning: Explanation of the analytical reasoning.
    """

    insight: str
    metric: str
    confidence: float
    confidence_components: ConfidenceComponents
    evidence: str
    reasoning: str


@dataclass
class Abstention:
    """An explicit abstention from generating an insight.

    When evidence is insufficient or confidence is below threshold,
    the system abstains rather than producing unreliable insights.

    Attributes:
        metric: Name of the behavioral metric.
        status: Always ``"ABSTAIN"``.
        reason: Human-readable explanation for the abstention.
        evidence_result: The evidence validation result that triggered abstention.
    """

    metric: str
    status: str = "ABSTAIN"
    reason: str = ""
    evidence_result: EvidenceResult | None = None


@dataclass
class AnalysisResult:
    """Complete result of the behavioral analysis pipeline.

    Aggregates all pipeline outputs into a single structure for
    serialization and report generation.

    Attributes:
        patterns: Detected behavioral trends.
        anomalies: Detected anomalies.
        insights: Generated insights (evidence-sufficient only).
        abstentions: Explicit abstentions (evidence-insufficient).
        dataset_schema: Discovered schema of the input dataset.
    """

    patterns: list[TrendResult]
    anomalies: list[Anomaly]
    insights: list[Insight]
    abstentions: list[Abstention]
    dataset_schema: DatasetSchema
