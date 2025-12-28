"""
Base parser class for DFS CSV parsing.

Provides shared functionality for currency cleaning, validation,
and the template method pattern for platform-specific parsers.
"""

import logging
import re
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

import pandas as pd

from src.models.dfs_entry import DFSEntry
from src.utils.constants import SPORT_ALIASES


logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract base class for DFS CSV parsers.

    Provides template method pattern for parsing, along with shared
    utilities for data cleaning and validation.

    Subclasses must implement:
        - _get_column_mapping(): Return dict mapping standard names to CSV columns
        - _get_source_name(): Return platform identifier ("DRAFTKINGS" or "FANDUEL")
        - _parse_date(): Parse date string to datetime
    """

    def __init__(self) -> None:
        """Initialize parser with empty warning list."""
        self.warnings: List[str] = []

    def parse(self, source: Union[str, Path, StringIO]) -> List[DFSEntry]:
        """
        Parse a CSV file into DFSEntry objects.

        This is the main entry point. Uses template method pattern -
        calls abstract methods implemented by subclasses for
        platform-specific behavior.

        Args:
            source: File path or StringIO containing CSV data

        Returns:
            List of validated DFSEntry objects

        Raises:
            ValueError: If required columns are missing
            FileNotFoundError: If file path doesn't exist
        """
        self.warnings = []  # Reset warnings
        df = self._read_csv(source)
        self._validate_columns(df)
        entries = self._parse_rows(df)
        return entries

    def _read_csv(self, source: Union[str, Path, StringIO]) -> pd.DataFrame:
        """
        Read CSV into DataFrame.

        Args:
            source: File path or StringIO

        Returns:
            DataFrame with CSV data
        """
        if isinstance(source, StringIO):
            source.seek(0)
            return pd.read_csv(source)

        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        return pd.read_csv(path, encoding='utf-8-sig')

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that required columns are present.

        Args:
            df: DataFrame to validate

        Raises:
            ValueError: If required columns are missing
        """
        mapping = self._get_column_mapping()
        required = set(mapping.values())
        present = set(df.columns)
        missing = required - present

        if missing:
            raise ValueError(
                f"Missing required columns for {self._get_source_name()}: {sorted(missing)}"
            )

    def _parse_rows(self, df: pd.DataFrame) -> List[DFSEntry]:
        """
        Parse each row into DFSEntry, skipping malformed rows.

        Args:
            df: DataFrame with CSV data

        Returns:
            List of successfully parsed entries
        """
        entries = []
        mapping = self._get_column_mapping()

        for idx, row in df.iterrows():
            try:
                entry = self._parse_single_row(row, mapping, idx)
                entries.append(entry)
            except Exception as e:
                warning = f"Row {idx}: Skipping due to error - {e}"
                self.warnings.append(warning)
                logger.warning(warning)

        return entries

    def _parse_single_row(
        self,
        row: pd.Series,
        mapping: Dict[str, str],
        row_idx: int
    ) -> DFSEntry:
        """
        Parse a single row into DFSEntry.

        Args:
            row: DataFrame row
            mapping: Column name mapping
            row_idx: Row index for error messages

        Returns:
            Parsed DFSEntry

        Raises:
            Various exceptions if row is malformed
        """
        # Extract values using mapping
        entry_id = str(row[mapping['entry_id']])
        contest_name = str(row[mapping['contest_name']])
        entry_fee = self._clean_currency(row[mapping['entry_fee']])
        winnings = self._clean_currency(row[mapping['winnings']])
        points = self._clean_points(row.get(mapping.get('points', ''), 0))
        sport = self._normalize_sport(str(row[mapping['sport']]))
        date = self._parse_date(str(row[mapping['date']]))

        return DFSEntry(
            entry_id=entry_id,
            date=date,
            sport=sport,
            contest_type="UNKNOWN",  # Will be classified later
            entry_fee=entry_fee,
            winnings=winnings,
            points=points,
            source=self._get_source_name(),
            contest_name=contest_name,
        )

    @staticmethod
    def _clean_currency(value: Any) -> Decimal:
        """
        Clean currency string to Decimal.

        Handles formats like:
        - "$5.00"
        - "5.00"
        - 5.00 (numeric)
        - "$1,234.56"

        Args:
            value: Currency value (string or numeric)

        Returns:
            Decimal representation

        Raises:
            ValueError: If value cannot be converted
        """
        if pd.isna(value):
            return Decimal('0')

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        # String cleaning
        value_str = str(value).strip()

        # Remove currency symbols and commas
        value_str = re.sub(r'[$,]', '', value_str)

        # Handle empty or dash (meaning zero)
        if not value_str or value_str == '-':
            return Decimal('0')

        try:
            return Decimal(value_str)
        except InvalidOperation:
            raise ValueError(f"Cannot convert '{value}' to currency")

    @staticmethod
    def _clean_points(value: Any) -> Decimal:
        """
        Clean points value to Decimal.

        Args:
            value: Points value (string or numeric)

        Returns:
            Decimal representation
        """
        if pd.isna(value):
            return Decimal('0')

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        value_str = str(value).strip()

        if not value_str or value_str == '-':
            return Decimal('0')

        try:
            return Decimal(value_str)
        except InvalidOperation:
            return Decimal('0')

    @staticmethod
    def _normalize_sport(sport: str) -> str:
        """
        Normalize sport name to standard code.

        Args:
            sport: Sport name from CSV

        Returns:
            Normalized sport code (uppercase)
        """
        sport = sport.strip().upper()

        # Check aliases
        if sport in SPORT_ALIASES:
            return SPORT_ALIASES[sport]

        return sport

    @abstractmethod
    def _get_column_mapping(self) -> Dict[str, str]:
        """
        Return mapping from standard names to platform column names.

        Returns:
            Dict with keys: entry_id, contest_name, entry_fee, winnings,
                           points, sport, date
        """
        pass

    @abstractmethod
    def _get_source_name(self) -> str:
        """
        Return platform identifier.

        Returns:
            "DRAFTKINGS" or "FANDUEL"
        """
        pass

    @abstractmethod
    def _parse_date(self, date_string: str) -> 'datetime':
        """
        Parse date string to datetime.

        Args:
            date_string: Date from CSV

        Returns:
            Parsed datetime object
        """
        pass
