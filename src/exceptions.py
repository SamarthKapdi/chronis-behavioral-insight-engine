"""
Custom exceptions for the Behavioral Insight Engine.

A dedicated exception hierarchy enables callers to handle
domain-specific errors separately from generic Python exceptions.
"""


class BehavioralInsightError(Exception):
    """Base exception for all Behavioral Insight Engine errors."""


class DataLoadError(BehavioralInsightError):
    """Raised when data loading or validation fails.

    Examples: file not found, empty CSV, unparseable dates.
    """


class InsufficientDataError(BehavioralInsightError):
    """Raised when there is not enough data for a required analysis step.

    Examples: fewer rows than the rolling window size requires.
    """


class SchemaValidationError(BehavioralInsightError):
    """Raised when the dataset schema does not meet requirements.

    Examples: no date column detected, no numeric columns found.
    """
