"""
Main pipeline orchestrator for the Behavioral Insight Engine.

This script is the single entry-point for running the full analysis
pipeline from the command line.  It chains together data loading,
pattern detection, anomaly detection, insight generation, and report
building, writing all outputs to the configured output directory.

Usage::

    python src/main.py                          # uses default data path
    python src/main.py data/my_custom_data.csv  # custom data path

All heavy lifting is delegated to purpose-built modules; this script
is responsible only for orchestration, I/O, and logging setup.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the ``src/`` package is importable regardless of working directory.
# ---------------------------------------------------------------------------
_SRC_DIR: Path = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_PROJECT_ROOT: Path = _SRC_DIR.parent

from anomaly_detector import detect_anomalies  # noqa: E402
from config import DEFAULT_DATA_PATH, DEFAULT_OUTPUT_DIR, MIN_OBSERVATIONS  # noqa: E402
from data_loader import load_behavioral_data  # noqa: E402
from exceptions import BehavioralInsightError  # noqa: E402
from insight_generator import generate_insights  # noqa: E402
from models import AnalysisResult  # noqa: E402
from pattern_detector import detect_patterns  # noqa: E402
from report_builder import build_report  # noqa: E402

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure root logging to stdout with a timestamped format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _resolve_data_path() -> Path:
    """Determine the data file path from CLI args or the default.

    Returns:
        Absolute ``Path`` to the data CSV file.
    """
    if len(sys.argv) > 1:
        raw_path: str = sys.argv[1]
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        return (_PROJECT_ROOT / candidate).resolve()
    return (_PROJECT_ROOT / DEFAULT_DATA_PATH).resolve()


def _write_json(data: list[dict], filepath: Path) -> None:
    """Serialise a list of dicts to a pretty-printed JSON file.

    Uses ``default=str`` to handle dates and other non-serialisable types.

    Args:
        data: The data to serialise.
        filepath: Destination file path.
    """
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    logger.info("Wrote %s (%d records)", filepath.name, len(data))


def main() -> None:
    """Execute the full Behavioral Insight Engine pipeline.

    Steps:
        1. Load and validate the input CSV.
        2. Detect behavioral trends (pattern detection).
        3. Detect statistical anomalies.
        4. Generate evidence-backed insights (with abstentions).
        5. Assemble the ``AnalysisResult``.
        6. Build the Markdown report.
        7. Write all outputs to the configured output directory.
    """
    _setup_logging()
    logger.info("=" * 60)
    logger.info("Behavioral Insight Engine - starting pipeline")
    logger.info("=" * 60)

    try:
        # ---------------------------------------------------------------
        # 1. Load data
        # ---------------------------------------------------------------
        data_path: Path = _resolve_data_path()
        logger.info("Data path: %s", data_path)

        df, schema, group_column = load_behavioral_data(str(data_path))
        logger.info(
            "Loaded dataset: %d rows, %d metric column(s), date range %s -> %s",
            schema.row_count,
            len(schema.metric_columns),
            schema.date_range[0],
            schema.date_range[1],
        )

        # ---------------------------------------------------------------
        # 2-4. Detect patterns, anomalies, generate insights
        #      (grouped or single-user)
        # ---------------------------------------------------------------
        if group_column is not None:
            groups = sorted(df[group_column].unique())
            logger.info(
                "Group column detected: '%s' (%d groups)",
                group_column,
                len(groups),
            )
            all_patterns = []
            all_anomalies = []
            all_insights = []
            all_abstentions = []

            for group_id in groups:
                logger.info("--- Analyzing group: %s ---", group_id)
                group_df = df[df[group_column] == group_id].reset_index(drop=True)

                group_metrics = [
                    m for m in schema.metric_columns
                    if group_df[m].notna().sum() >= MIN_OBSERVATIONS
                ]

                g_patterns = detect_patterns(group_df, group_metrics)
                g_anomalies = detect_anomalies(group_df, group_metrics)
                g_insights, g_abstentions = generate_insights(
                    g_patterns, g_anomalies, group_df
                )

                # Tag each result with user_id
                for p in g_patterns:
                    p.supporting_statistics["user_id"] = str(group_id)
                for a in g_anomalies:
                    a.explanation = f"[{group_id}] {a.explanation}"
                for i in g_insights:
                    i.insight = f"[{group_id}] {i.insight}"
                    i.reasoning = f"[{group_id}] {i.reasoning}"
                for ab in g_abstentions:
                    ab.reason = f"[{group_id}] {ab.reason}"

                all_patterns.extend(g_patterns)
                all_anomalies.extend(g_anomalies)
                all_insights.extend(g_insights)
                all_abstentions.extend(g_abstentions)

            patterns = all_patterns
            anomalies = all_anomalies
            insights = all_insights
            abstentions = all_abstentions
        else:
            patterns = detect_patterns(df, schema.metric_columns)
            anomalies = detect_anomalies(df, schema.metric_columns)
            insights, abstentions = generate_insights(patterns, anomalies, df)

        logger.info("Detected %d pattern(s)", len(patterns))
        logger.info("Detected %d anomaly/anomalies", len(anomalies))
        logger.info(
            "Generated %d insight(s), %d abstention(s)",
            len(insights),
            len(abstentions),
        )

        # ---------------------------------------------------------------
        # 5. Assemble result
        # ---------------------------------------------------------------
        result = AnalysisResult(
            patterns=patterns,
            anomalies=anomalies,
            insights=insights,
            abstentions=abstentions,
            dataset_schema=schema,
        )

        # ---------------------------------------------------------------
        # 6. Build report
        # ---------------------------------------------------------------
        report_md: str = build_report(result)

        # ---------------------------------------------------------------
        # 7. Write outputs
        # ---------------------------------------------------------------
        output_dir: Path = _PROJECT_ROOT / DEFAULT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        logger.info("Output directory: %s", output_dir)

        _write_json(
            [asdict(p) for p in patterns],
            output_dir / "patterns.json",
        )
        _write_json(
            [asdict(a) for a in anomalies],
            output_dir / "anomalies.json",
        )
        _write_json(
            [asdict(i) for i in insights],
            output_dir / "insights.json",
        )

        # Abstentions may have None evidence_result — asdict handles this
        # but we convert explicitly for clarity.
        abstention_dicts: list[dict] = []
        for ab in abstentions:
            ab_dict = asdict(ab)
            if ab_dict.get("evidence_result") is None:
                ab_dict["evidence_result"] = None
            abstention_dicts.append(ab_dict)
        _write_json(abstention_dicts, output_dir / "abstentions.json")

        report_path: Path = output_dir / "report.md"
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(report_md)
        logger.info("Wrote report.md (%d characters)", len(report_md))

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        logger.info("=" * 60)
        logger.info(
            "Pipeline complete. Found %d patterns, %d anomalies, "
            "%d insights, %d abstentions.",
            len(patterns),
            len(anomalies),
            len(insights),
            len(abstentions),
        )
        logger.info("=" * 60)

    except BehavioralInsightError as exc:
        logger.error("Pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
