"""
FanDuel CSV parser.

Parses FanDuel contest entry export format into normalized DFSEntry objects.
"""

from datetime import datetime
from typing import Dict

from .base_parser import BaseParser
from src.utils.constants import (
    PLATFORM_FANDUEL,
    FD_COLUMN_ENTRY_ID,
    FD_COLUMN_CONTEST_NAME,
    FD_COLUMN_ENTRY_FEE,
    FD_COLUMN_WINNINGS,
    FD_COLUMN_POINTS,
    FD_COLUMN_SPORT,
    FD_COLUMN_DATE,
)
from src.utils.date_parser import parse_date


class FanDuelParser(BaseParser):
    """
    Parser for FanDuel CSV exports.

    Expected columns:
    - Entry Id
    - Contest
    - Entry Fee
    - Winnings
    - Points
    - Sport
    - Entered

    Note: FanDuel uses slightly different column names than DraftKings
    (e.g., "Entry Id" vs "Entry ID", "Contest" vs "Contest Name").

    Example usage:
        parser = FanDuelParser()
        entries = parser.parse("fanduel_export.csv")
    """

    def _get_column_mapping(self) -> Dict[str, str]:
        """
        Return FanDuel column mapping.

        Maps standardized field names to actual FanDuel column headers.
        """
        return {
            'entry_id': FD_COLUMN_ENTRY_ID,
            'contest_name': FD_COLUMN_CONTEST_NAME,
            'entry_fee': FD_COLUMN_ENTRY_FEE,
            'winnings': FD_COLUMN_WINNINGS,
            'points': FD_COLUMN_POINTS,
            'sport': FD_COLUMN_SPORT,
            'date': FD_COLUMN_DATE,
        }

    def _get_source_name(self) -> str:
        """Return FanDuel platform identifier."""
        return PLATFORM_FANDUEL

    def _parse_date(self, date_string: str) -> datetime:
        """
        Parse FanDuel date format.

        FanDuel uses various formats including:
        - "Sep 15, 2024 1:00PM"
        - "Sep 15, 2024 1:00 PM"
        - "2024-09-15"
        - "09/15/2024"

        Args:
            date_string: Date string from CSV

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If date cannot be parsed
        """
        return parse_date(date_string)
