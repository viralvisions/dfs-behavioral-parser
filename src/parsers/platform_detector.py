"""
Platform detector for DFS CSV exports.

Automatically detects whether a CSV file is from DraftKings or FanDuel
by inspecting the column headers.
"""

import csv
from io import StringIO
from pathlib import Path
from typing import Union, Set, List

from src.utils.constants import (
    PLATFORM_DRAFTKINGS,
    PLATFORM_FANDUEL,
    DK_REQUIRED_COLUMNS,
    FD_REQUIRED_COLUMNS,
)


def detect_platform(source: Union[str, Path, StringIO]) -> str:
    """
    Detect the DFS platform from a CSV file or string.

    Inspects the first row (headers) to determine if the format
    matches DraftKings or FanDuel column conventions.

    Args:
        source: File path, Path object, or StringIO containing CSV data

    Returns:
        Platform identifier: "DRAFTKINGS" or "FANDUEL"

    Raises:
        ValueError: If platform cannot be detected from headers
        FileNotFoundError: If file path doesn't exist

    Examples:
        >>> detect_platform("contests.csv")
        "DRAFTKINGS"

        >>> detect_platform(StringIO("Entry Id,Contest,..."))
        "FANDUEL"
    """
    headers = _extract_headers(source)
    return _identify_platform(headers)


def detect_platform_from_headers(headers: List[str]) -> str:
    """
    Detect platform from a list of column headers.

    Args:
        headers: List of column header strings

    Returns:
        Platform identifier: "DRAFTKINGS" or "FANDUEL"

    Raises:
        ValueError: If headers don't match any known platform
    """
    return _identify_platform(set(headers))


def _extract_headers(source: Union[str, Path, StringIO]) -> Set[str]:
    """
    Extract column headers from CSV source.

    Args:
        source: File path or StringIO

    Returns:
        Set of header column names
    """
    if isinstance(source, StringIO):
        # Reset to beginning
        source.seek(0)
        reader = csv.reader(source)
        headers = next(reader, [])
        source.seek(0)  # Reset for subsequent reads
        return set(headers)

    # File path
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader, [])

    return set(headers)


def _identify_platform(headers: Set[str]) -> str:
    """
    Identify platform from header set.

    Uses a scoring system - the platform with more matching required
    columns wins. This allows for some column variations while still
    reliably detecting the platform.

    Args:
        headers: Set of column header names

    Returns:
        Platform identifier

    Raises:
        ValueError: If no clear platform match
    """
    # Normalize headers to handle case variations
    headers_normalized = {h.strip() for h in headers}

    # Count matches for each platform
    dk_matches = len(DK_REQUIRED_COLUMNS & headers_normalized)
    fd_matches = len(FD_REQUIRED_COLUMNS & headers_normalized)

    # DraftKings requires most of its columns
    dk_threshold = len(DK_REQUIRED_COLUMNS) - 1  # Allow 1 missing

    # FanDuel requires most of its columns
    fd_threshold = len(FD_REQUIRED_COLUMNS) - 1  # Allow 1 missing

    # Check DraftKings first (more common)
    if dk_matches >= dk_threshold:
        return PLATFORM_DRAFTKINGS

    # Check FanDuel
    if fd_matches >= fd_threshold:
        return PLATFORM_FANDUEL

    # Neither matched - provide helpful error
    missing_dk = DK_REQUIRED_COLUMNS - headers_normalized
    missing_fd = FD_REQUIRED_COLUMNS - headers_normalized

    raise ValueError(
        f"Could not detect platform from CSV headers.\n"
        f"Found headers: {sorted(headers_normalized)[:5]}...\n"
        f"For DraftKings, missing: {sorted(missing_dk)}\n"
        f"For FanDuel, missing: {sorted(missing_fd)}"
    )


def is_draftkings(source: Union[str, Path, StringIO]) -> bool:
    """
    Check if source is a DraftKings CSV.

    Args:
        source: File path or StringIO

    Returns:
        True if DraftKings format, False otherwise
    """
    try:
        return detect_platform(source) == PLATFORM_DRAFTKINGS
    except (ValueError, FileNotFoundError):
        return False


def is_fanduel(source: Union[str, Path, StringIO]) -> bool:
    """
    Check if source is a FanDuel CSV.

    Args:
        source: File path or StringIO

    Returns:
        True if FanDuel format, False otherwise
    """
    try:
        return detect_platform(source) == PLATFORM_FANDUEL
    except (ValueError, FileNotFoundError):
        return False
