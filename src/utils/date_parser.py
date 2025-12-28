"""
Date parser utility for flexible date parsing.

Handles multiple date formats from DraftKings, FanDuel, and other sources.
"""

from datetime import datetime
from typing import Optional, List

from .constants import DATE_FORMATS


def parse_date(date_string: str, formats: Optional[List[str]] = None) -> datetime:
    """
    Parse a date string using multiple format attempts.

    Tries each format in order until one succeeds. This handles the
    variety of date formats encountered in DFS platform CSV exports.

    Args:
        date_string: The date string to parse
        formats: Optional list of format strings to try.
                 Defaults to DATE_FORMATS from constants.

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If no format matches the input string

    Examples:
        >>> parse_date("2024-09-15 13:00:00")
        datetime.datetime(2024, 9, 15, 13, 0)

        >>> parse_date("Sep 15, 2024 1:00PM")
        datetime.datetime(2024, 9, 15, 13, 0)
    """
    if formats is None:
        formats = DATE_FORMATS

    date_string = date_string.strip()

    # Handle empty strings
    if not date_string:
        raise ValueError("Date string cannot be empty")

    # Try each format
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    # If none worked, raise helpful error
    raise ValueError(
        f"Could not parse date '{date_string}'. "
        f"Tried formats: {formats[:3]}... "
        f"(and {len(formats) - 3} more)"
    )


def parse_date_safe(date_string: str, default: Optional[datetime] = None) -> Optional[datetime]:
    """
    Parse a date string, returning default on failure instead of raising.

    Args:
        date_string: The date string to parse
        default: Value to return if parsing fails (default: None)

    Returns:
        Parsed datetime or default value

    Examples:
        >>> parse_date_safe("2024-09-15")
        datetime.datetime(2024, 9, 15, 0, 0)

        >>> parse_date_safe("invalid", datetime(2024, 1, 1))
        datetime.datetime(2024, 1, 1, 0, 0)
    """
    try:
        return parse_date(date_string)
    except ValueError:
        return default


def normalize_date_format(dt: datetime) -> str:
    """
    Convert datetime to standard ISO format string.

    Args:
        dt: Datetime object to format

    Returns:
        ISO format string (YYYY-MM-DD HH:MM:SS)
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_date_only(dt: datetime) -> str:
    """
    Extract date portion only (no time).

    Args:
        dt: Datetime object

    Returns:
        Date string (YYYY-MM-DD)
    """
    return dt.strftime("%Y-%m-%d")
