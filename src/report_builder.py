"""
Report builder for the Behavioral Insight Engine.

Generates a professional, self-contained Markdown report from an
``AnalysisResult``.  The report is designed to be immediately
readable by non-technical stakeholders while still providing full
methodological transparency for reviewers.

Sections:
    1. Title & timestamp
    2. Executive Summary
    3. Behavioral Trends (full table)
    4. Significant Changes (>20% magnitude)
    5. Anomalies
    6. Insights (with confidence bars)
    7. Abstentions
    8. Methodology
    9. Limitations
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from models import AnalysisResult, Anomaly, Insight, TrendResult

logger = logging.getLogger(__name__)


def build_report(result: AnalysisResult) -> str:
    """Build a complete Markdown analysis report.

    Args:
        result: The aggregated ``AnalysisResult`` from the pipeline.

    Returns:
        A string containing the full Markdown report, ready to be
        written to disk.
    """
    sections: list[str] = [
        _section_title(),
        _section_executive_summary(result),
        _section_behavioral_trends(result.patterns),
        _section_significant_changes(result.patterns),
        _section_anomalies(result.anomalies),
        _section_insights(result.insights),
        _section_abstentions(result),
        _section_methodology(),
        _section_limitations(result),
    ]

    report: str = "\n\n".join(sections)
    logger.info("Report generated: %d characters", len(report))
    return report


# ======================================================================
# Section builders
# ======================================================================


def _section_title() -> str:
    """Generate the report title with a UTC timestamp."""
    timestamp: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        "# Behavioral Insight Engine — Analysis Report\n\n"
        f"**Generated:** {timestamp}"
    )


def _section_executive_summary(result: AnalysisResult) -> str:
    """Provide high-level counts and dataset metadata."""
    schema = result.dataset_schema
    lines: list[str] = [
        "## Executive Summary",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| Patterns detected | {len(result.patterns)} |",
        f"| Anomalies detected | {len(result.anomalies)} |",
        f"| Insights generated | {len(result.insights)} |",
        f"| Abstentions | {len(result.abstentions)} |",
        "",
        f"- **Date range:** {schema.date_range[0]} to {schema.date_range[1]}",
        f"- **Total observations:** {schema.row_count}",
        f"- **Metrics analysed:** {', '.join(schema.metric_columns)}",
    ]
    return "\n".join(lines)


def _section_behavioral_trends(patterns: list[TrendResult]) -> str:
    """Table of all detected trends."""
    lines: list[str] = [
        "## Behavioral Trends",
        "",
    ]

    if not patterns:
        lines.append("_No behavioral trends detected._")
        return "\n".join(lines)

    lines.extend([
        "| Metric | Direction | % Change | Slope (/day) | R² | p-value | Significant |",
        "|--------|-----------|----------|-------------:|----:|--------:|:-----------:|",
    ])

    for p in patterns:
        sig: str = "✅" if p.p_value < 0.05 else "—"
        lines.append(
            f"| {p.metric} | {p.trend_direction} | "
            f"{p.percent_change:+.1f}% | {p.slope:.4f} | "
            f"{p.r_squared:.3f} | {p.p_value:.4f} | {sig} |"
        )

    return "\n".join(lines)


def _section_significant_changes(patterns: list[TrendResult]) -> str:
    """Highlight trends with more than 20% change."""
    significant: list[TrendResult] = [
        p for p in patterns if abs(p.percent_change) > 20.0
    ]

    lines: list[str] = [
        "## Significant Changes",
        "",
    ]

    if not significant:
        lines.append("_No significant changes (>20% magnitude) detected._")
        return "\n".join(lines)

    lines.append(
        "The following metrics showed particularly large shifts:\n"
    )

    for p in significant:
        direction_word: str = "increased" if p.percent_change > 0 else "decreased"
        metric_label: str = p.metric.replace("_", " ")
        lines.append(
            f"- **{metric_label}** {direction_word} by "
            f"**{abs(p.percent_change):.1f}%** "
            f"(from {p.previous_mean:.1f} to {p.recent_mean:.1f})"
        )

    return "\n".join(lines)


def _section_anomalies(anomalies: list[Anomaly]) -> str:
    """Table of detected anomalies."""
    lines: list[str] = [
        "## Anomalies",
        "",
    ]

    if not anomalies:
        lines.append("_No anomalies detected._")
        return "\n".join(lines)

    lines.extend([
        "| Date | Metric | Observed | Expected | Deviation | Methods | Explanation |",
        "|------|--------|--------:|---------:|----------:|---------|-------------|",
    ])

    for a in anomalies:
        methods_str: str = ", ".join(a.methods_triggered)
        lines.append(
            f"| {a.date} | {a.metric} | {a.observed_value:.1f} | "
            f"{a.expected_value:.1f} | {a.deviation:.2f} | "
            f"{methods_str} | {a.explanation} |"
        )

    return "\n".join(lines)


def _section_insights(insights: list[Insight]) -> str:
    """Each insight as a subsection with a visual confidence bar."""
    lines: list[str] = [
        "## Insights",
        "",
    ]

    if not insights:
        lines.append("_No insights generated (insufficient evidence or confidence)._")
        return "\n".join(lines)

    for idx, ins in enumerate(insights, start=1):
        metric_label: str = ins.metric.replace("_", " ")
        conf_pct: float = ins.confidence * 100
        bar: str = _render_confidence_bar(ins.confidence)

        lines.extend([
            f"### {idx}. {metric_label.title()}",
            "",
            f"> {ins.insight}",
            "",
            f"**Confidence:** {conf_pct:.0f}% {bar}",
            "",
            "| Component | Score |",
            "|-----------|------:|",
            f"| Sample size | {ins.confidence_components.sample_score:.3f} |",
            f"| Trend strength | {ins.confidence_components.trend_score:.3f} |",
            f"| Consistency | {ins.confidence_components.consistency_score:.3f} |",
            f"| Variance | {ins.confidence_components.variance_score:.3f} |",
            "",
            f"**Evidence:** {ins.evidence}",
            "",
            f"**Reasoning:** {ins.reasoning}",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def _section_abstentions(result: AnalysisResult) -> str:
    """List metrics where the engine abstained."""
    lines: list[str] = [
        "## Abstentions",
        "",
    ]

    if not result.abstentions:
        lines.append("_No abstentions — all metrics met evidence and confidence thresholds._")
        return "\n".join(lines)

    lines.append(
        "The engine abstained from generating insights for the "
        "following metrics:\n"
    )

    for ab in result.abstentions:
        lines.append(f"- **{ab.metric}**: {ab.reason}")

    return "\n".join(lines)


def _section_methodology() -> str:
    """Describe the analytical pipeline."""
    return """## Methodology

This report was generated by the **Behavioral Insight Engine**, a deterministic
statistical pipeline that processes daily behavioral data through four stages:

1. **Window Comparison** — A rolling-window approach compares the most recent
   *N*-day window against the preceding *N*-day window.  Percent change between
   the two windows determines trend direction and magnitude.

2. **Linear Regression** — Ordinary least squares regression is fitted over
   the full time series for each metric.  The slope, R², and p-value quantify
   trend strength and statistical significance.

3. **Anomaly Detection** — Three independent methods identify outliers:
   - **Z-score**: flags observations more than 2.5 standard deviations from
     the mean.
   - **IQR (Interquartile Range)**: flags observations outside
     *Q1 − 1.5×IQR* to *Q3 + 1.5×IQR*.
   - **Rolling deviation**: flags observations more than 2.0 rolling standard
     deviations from the rolling mean (7-day window).

4. **Confidence Scoring** — Each potential insight receives a weighted
   confidence score combining:
   - Sample size (weight 0.25, saturates at 30 observations)
   - Trend strength (weight 0.35, saturates at 50% change)
   - Consistency (weight 0.25, fraction of days following trend)
   - Variance stability (weight 0.15, inverse of coefficient of variation)

   Insights are only emitted when confidence ≥ 0.60.

5. **Evidence Thresholds** — Before scoring, each metric must pass:
   - ≥ 7 non-missing observations
   - Coefficient of variation > 0.01
   - |Percent change| ≥ 5.0%"""


def _section_limitations(result: AnalysisResult) -> str:
    """Caveats and disclaimers."""
    row_count: int = result.dataset_schema.row_count
    return f"""## Limitations

- **Dataset size**: This analysis is based on {row_count} observations.
  Larger datasets may reveal additional patterns or reduce false positives.
- **Synthetic data caveat**: If the input data is synthetically generated,
  detected patterns may not reflect real-world behavioral dynamics.
- **No causal claims**: All findings are correlational.  This engine does
  not establish causal relationships between metrics.
- **No medical or psychological interpretation**: This tool performs
  statistical analysis only.  Outputs should not be interpreted as
  medical, psychological, or diagnostic assessments.
- **Temporal scope**: The analysis reflects the date range covered by the
  input data and may not generalise to other time periods."""


# ======================================================================
# Internal helpers
# ======================================================================


def _render_confidence_bar(confidence: float, width: int = 20) -> str:
    """Render a simple text-based confidence bar.

    Args:
        confidence: Confidence value in [0, 1].
        width: Total number of characters in the bar.

    Returns:
        A string like ``[████████████░░░░░░░░]``.
    """
    filled: int = round(confidence * width)
    empty: int = width - filled
    return f"[{'█' * filled}{'░' * empty}]"
