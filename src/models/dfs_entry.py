"""
DFSEntry model - Normalized representation of a single DFS contest entry.

This model represents a single entry from either DraftKings or FanDuel,
normalized to a common format for analysis. Uses Decimal for all money
fields to ensure financial precision.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any


@dataclass
class DFSEntry:
    """
    Normalized representation of a single DFS contest entry.

    Represents a single entry in a DFS contest from any supported platform,
    with all data normalized to a common format. Uses Decimal for financial
    calculations to avoid floating-point precision errors.

    Attributes:
        entry_id: Unique identifier for this entry (e.g., "12345")
        date: When the entry was made
        sport: Sport code in uppercase (NFL, NBA, NHL, MLB, etc.)
        contest_type: Type of contest (GPP, CASH, H2H, MULTI, UNKNOWN)
        entry_fee: Amount wagered (use Decimal for precision)
        winnings: Amount won (use Decimal for precision)
        points: Fantasy points scored
        source: Platform identifier ("DRAFTKINGS" or "FANDUEL")
        contest_name: Original contest name (for debugging/reference)

    Properties:
        roi: Return on investment as percentage
        profit: Net profit/loss
        is_winning_entry: Whether this entry made money
    """

    entry_id: str
    date: datetime
    sport: str
    contest_type: str
    entry_fee: Decimal
    winnings: Decimal
    points: Decimal
    source: str
    contest_name: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Validate and normalize entry data after initialization.

        Raises:
            ValueError: If entry_fee is negative
            ValueError: If winnings is negative
            ValueError: If source is not DRAFTKINGS or FANDUEL
        """
        # Validate entry_fee is non-negative
        if self.entry_fee < Decimal('0'):
            raise ValueError(
                f"Entry fee cannot be negative: {self.entry_fee}"
            )

        # Validate winnings is non-negative
        if self.winnings < Decimal('0'):
            raise ValueError(
                f"Winnings cannot be negative: {self.winnings}"
            )

        # Validate source is a known platform
        valid_sources = {'DRAFTKINGS', 'FANDUEL'}
        if self.source.upper() not in valid_sources:
            raise ValueError(
                f"Invalid source '{self.source}'. Must be one of: {valid_sources}"
            )

        # Normalize source to uppercase
        object.__setattr__(self, 'source', self.source.upper())

        # Normalize sport to uppercase
        object.__setattr__(self, 'sport', self.sport.upper())

    @property
    def roi(self) -> Decimal:
        """
        Calculate return on investment as a percentage.

        ROI = ((winnings - entry_fee) / entry_fee) * 100

        Returns:
            ROI as percentage (e.g., 110.00 for 110% ROI)
            Returns 0 if entry_fee is zero to avoid division by zero
        """
        if self.entry_fee == Decimal('0'):
            return Decimal('0')
        return ((self.winnings - self.entry_fee) / self.entry_fee) * Decimal('100')

    @property
    def profit(self) -> Decimal:
        """
        Calculate net profit or loss for this entry.

        Returns:
            Profit (positive) or loss (negative) as Decimal
        """
        return self.winnings - self.entry_fee

    @property
    def is_winning_entry(self) -> bool:
        """
        Check if this entry was profitable.

        Returns:
            True if winnings exceed entry_fee, False otherwise
        """
        return self.winnings > self.entry_fee

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize entry to dictionary for JSON output.

        All Decimal values are converted to strings to preserve precision.
        Datetime is converted to ISO format string.

        Returns:
            Dictionary representation of the entry
        """
        return {
            'entry_id': self.entry_id,
            'date': self.date.isoformat(),
            'sport': self.sport,
            'contest_type': self.contest_type,
            'entry_fee': str(self.entry_fee),
            'winnings': str(self.winnings),
            'points': str(self.points),
            'source': self.source,
            'contest_name': self.contest_name,
            'roi': str(self.roi),
            'profit': str(self.profit),
            'is_winning_entry': self.is_winning_entry,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DFSEntry':
        """
        Create DFSEntry from dictionary.

        Args:
            data: Dictionary with entry fields

        Returns:
            New DFSEntry instance
        """
        # Parse date if it's a string
        date_value = data['date']
        if isinstance(date_value, str):
            date_value = datetime.fromisoformat(date_value)

        return cls(
            entry_id=data['entry_id'],
            date=date_value,
            sport=data['sport'],
            contest_type=data['contest_type'],
            entry_fee=Decimal(str(data['entry_fee'])),
            winnings=Decimal(str(data['winnings'])),
            points=Decimal(str(data['points'])),
            source=data['source'],
            contest_name=data.get('contest_name'),
        )
