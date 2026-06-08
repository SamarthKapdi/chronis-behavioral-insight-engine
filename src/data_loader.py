"""
Data loading and schema discovery for the Behavioral Insight Engine.

Provides ``load_behavioral_data`` which reads a CSV file, automatically
detects date and numeric metric columns, validates the discovered schema,
and returns a cleaned DataFrame alongside a :class:`DatasetSchema` that
describes the structure of the loaded dataset.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from models import DatasetSchema
from config import MIN_OBSERVATIONS
from exceptions import DataLoadError, SchemaValidationError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_date_column(df: pd.DataFrame) -> str:
    """Identify the date column by name convention or datetime parseability.

    Strategy:
        1. Look for a column whose lowercased name contains ``"date"``.
        2. Fall back to the first column that can be parsed as datetime.

    Parameters
    ----------
    df:
        Raw DataFrame loaded from CSV.

    Returns
    -------
    str
        Name of the detected date column.

    Raises
    ------
    SchemaValidationError
        If no date column can be identified.
    """
    # Strategy 1 — name-based detection
    for col in df.columns:
        if "date" in col.lower():
            try:
                pd.to_datetime(df[col])
                logger.info("Date column detected by name: '%s'", col)
                return col
            except (ValueError, TypeError):
                logger.debug(
                    "Column '%s' matched name heuristic but could not be "
                    "parsed as datetime; skipping.",
                    col,
                )

    # Strategy 2 — brute-force parse attempt on object/string columns
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            try:
                pd.to_datetime(df[col])
                logger.info(
                    "Date column detected by parsing: '%s'", col
                )
                return col
            except (ValueError, TypeError):
                continue

    raise SchemaValidationError(
        "No date column detected. Ensure the CSV contains a column with "
        "dates (named 'date' or parseable as datetime)."
    )


def _detect_metric_columns(
    df: pd.DataFrame, date_column: str
) -> list[str]:
    """Return all numeric columns excluding the date column and ID-like columns.

    Columns whose lowered name contains ``'id'`` or ``'user'`` **and** that
    have very few unique values (≤ 10) relative to the row count are
    considered grouping/ID columns and are excluded from metrics.

    Parameters
    ----------
    df:
        DataFrame with at least the date column already identified.
    date_column:
        Name of the date column to exclude.

    Returns
    -------
    list[str]
        Sorted list of numeric metric column names.

    Raises
    ------
    SchemaValidationError
        If no numeric metric columns are found.
    """
    numeric_cols = [
        col
        for col in df.select_dtypes(include="number").columns
        if col != date_column
    ]

    # Exclude numeric columns that look like ID / grouping columns
    filtered_cols: list[str] = []
    for col in numeric_cols:
        col_lower = col.lower()
        if ("id" in col_lower or "user" in col_lower) and df[col].nunique() <= 10:
            logger.info(
                "Excluding numeric column '%s' from metrics (looks like an "
                "ID/grouping column with %d unique values).",
                col,
                df[col].nunique(),
            )
            continue
        filtered_cols.append(col)

    if not filtered_cols:
        raise SchemaValidationError(
            "No numeric metric columns found in the dataset. "
            "At least one numeric column (besides the date) is required."
        )
    metric_columns = sorted(filtered_cols)
    logger.info("Detected %d metric columns: %s", len(metric_columns), metric_columns)
    return metric_columns


def _detect_group_column(df: pd.DataFrame, date_column: str) -> str | None:
    """Detect a grouping/ID column (e.g. ``user_id``) if present.

    Strategy:
        Look for a string/object column whose lowercased name contains
        ``'user'`` or ``'id'`` (but not ``'date'``), and which has
        relatively few unique values compared to the row count.

    Parameters
    ----------
    df:
        The loaded DataFrame.
    date_column:
        Name of the date column (to exclude from candidates).

    Returns
    -------
    str | None
        The detected group column name, or ``None`` if no grouping
        column is found.
    """
    for col in df.columns:
        col_lower = col.lower()
        if col == date_column:
            continue
        if "date" in col_lower:
            continue
        if "user" in col_lower or "id" in col_lower:
            # Must be string/object type OR have few unique values
            is_string = df[col].dtype == object or pd.api.types.is_string_dtype(df[col])
            n_unique = df[col].nunique()
            few_unique = n_unique <= max(10, len(df) // 10)
            if is_string or few_unique:
                logger.info(
                    "Group column detected: '%s' with %d unique values",
                    col,
                    n_unique,
                )
                return col
    return None




def _compute_missing_counts(
    df: pd.DataFrame, columns: list[str]
) -> dict[str, int]:
    """Count missing values per column.

    Parameters
    ----------
    df:
        The DataFrame to inspect.
    columns:
        Columns to check.

    Returns
    -------
    dict[str, int]
        Mapping of column name → count of missing values.
    """
    counts: dict[str, int] = {}
    for col in columns:
        n_missing = int(df[col].isna().sum())
        counts[col] = n_missing
        if n_missing > 0:
            logger.warning(
                "Column '%s' has %d missing value(s).", col, n_missing
            )
    return counts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_behavioral_data(
    path: str,
) -> tuple[pd.DataFrame, DatasetSchema, str | None]:
    """Load a behavioural-data CSV and return a cleaned DataFrame with schema.

    The function performs the following steps:

    1. **Read** the CSV file from *path*.
    2. **Detect** the date column (by name or parseability).
    3. **Parse** dates and sort chronologically.
    4. **Detect** numeric metric columns dynamically.
    5. **Detect** an optional grouping column (e.g. ``user_id``).
    6. **Validate** that at least one metric column exists and the
       DataFrame is non-empty.
    7. **Log** any missing values but retain all rows.
    8. **Return** the cleaned DataFrame, a ``DatasetSchema``, and the
       detected group column name (or ``None``).

    Parameters
    ----------
    path:
        Filesystem path to the CSV file.

    Returns
    -------
    tuple[pd.DataFrame, DatasetSchema, str | None]
        A 3-tuple of the cleaned DataFrame, the discovered schema, and
        the name of the detected group column (``None`` if not found).

    Raises
    ------
    DataLoadError
        If the file cannot be read (not found, permission error, empty file).
    SchemaValidationError
        If the schema fails validation (no date column, no metrics, etc.).
    """
    # ------------------------------------------------------------------
    # 1. Read CSV
    # ------------------------------------------------------------------
    file_path = Path(path)
    if not file_path.exists():
        raise DataLoadError(f"File not found: {path}")

    try:
        df = pd.read_csv(file_path)
    except PermissionError as exc:
        raise DataLoadError(
            f"Permission denied when reading '{path}'."
        ) from exc
    except Exception as exc:
        raise DataLoadError(
            f"Failed to read CSV file '{path}': {exc}"
        ) from exc

    if df.empty:
        raise DataLoadError(f"CSV file is empty: {path}")

    logger.info(
        "Loaded CSV with %d rows and %d columns from '%s'.",
        len(df),
        len(df.columns),
        path,
    )

    # ------------------------------------------------------------------
    # 2. Detect and parse date column
    # ------------------------------------------------------------------
    date_column = _detect_date_column(df)

    try:
        df[date_column] = pd.to_datetime(df[date_column])
    except Exception as exc:
        raise SchemaValidationError(
            f"Could not parse column '{date_column}' as datetime: {exc}"
        ) from exc

    # ------------------------------------------------------------------
    # 3. Sort chronologically
    # ------------------------------------------------------------------
    df = df.sort_values(by=date_column).reset_index(drop=True)
    logger.info("Data sorted chronologically by '%s'.", date_column)

    # ------------------------------------------------------------------
    # 4. Detect metric columns
    # ------------------------------------------------------------------
    metric_columns = _detect_metric_columns(df, date_column)

    # ------------------------------------------------------------------
    # 5. Validate row count
    # ------------------------------------------------------------------
    if len(df) < MIN_OBSERVATIONS:
        raise SchemaValidationError(
            f"Dataset has {len(df)} row(s), but at least "
            f"{MIN_OBSERVATIONS} are required for analysis."
        )

    # ------------------------------------------------------------------
    # 6. Compute missing-value counts (log warnings, keep all rows)
    # ------------------------------------------------------------------
    all_columns = [date_column] + metric_columns
    missing_counts = _compute_missing_counts(df, all_columns)

    # ------------------------------------------------------------------
    # 7. Build schema and return
    # ------------------------------------------------------------------
    earliest = df[date_column].min().strftime("%Y-%m-%d")
    latest = df[date_column].max().strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # 7b. Detect group column (e.g. user_id)
    # ------------------------------------------------------------------
    group_column = _detect_group_column(df, date_column)

    schema = DatasetSchema(
        date_column=date_column,
        metric_columns=metric_columns,
        row_count=len(df),
        date_range=(earliest, latest),
        missing_value_counts=missing_counts,
        group_column=group_column,
    )

    logger.info(
        "Schema discovery complete - date column: '%s', "
        "%d metrics, %d rows, date range: %s to %s.",
        schema.date_column,
        len(schema.metric_columns),
        schema.row_count,
        earliest,
        latest,
    )

    return df, schema, group_column
