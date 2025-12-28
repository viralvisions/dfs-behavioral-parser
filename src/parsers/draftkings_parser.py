"""
DraftKings CSV parser.

Parses DraftKings contest entry export format into normalized DFSEntry objects.
"""

from datetime import datetime
from typing import Dict

from .base_parser import BaseParser
from src.utils.constants import (
    PLATFORM_DRAFTKINGS,
    DK_COLUMN_ENTRY_ID,
    DK_COLUMN_CONTEST_NAME,
    DK_COLUMN_ENTRY_FEE,
    DK_COLUMN_WINNINGS,
    DK_COLUMN_POINTS,
    DK_COLUMN_SPORT,
    DK_COLUMN_DATE,
)
from src.utils.date_parser import parse_date


class DraftKingsParser(BaseParser):
    """
    Parser for DraftKings CSV exports.

    Expected columns:
    - Entry ID
    - Contest Name
    - Entry Fee
    - Winnings
    - Points
    - Sport
    - Date Entered

    Example usage:
        parser = DraftKingsParser()
        entries = parser.parse("draftkings_export.csv")
    """

    def _get_column_mapping(self) -> Dict[str, str]:
        """
        Return DraftKings column mapping.

        Maps standardized field names to actual DraftKings column headers.
        """
        return {
            'entry_id': DK_COLUMN_ENTRY_ID,
            'contest_name': DK_COLUMN_CONTEST_NAME,
            'entry_fee': DK_COLUMN_ENTRY_FEE,
            'winnings': DK_COLUMN_WINNINGS,
            'points': DK_COLUMN_POINTS,
            'sport': DK_COLUMN_SPORT,
            'date': DK_COLUMN_DATE,
        }

    def _get_source_name(self) -> str:
        """Return DraftKings platform identifier."""
        return PLATFORM_DRAFTKINGS

    def _parse_date(self, date_string: str) -> datetime:
        """
        Parse DraftKings date format.

        DraftKings typically uses formats like:
        - "2024-09-15 13:00:00"
        - "2024-09-15"
        - "09/15/2024 1:00 PM"

        Args:
            date_string: Date string from CSV

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If date cannot be parsed
        """
        return parse_date(date_string)
