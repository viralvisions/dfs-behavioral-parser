"""
DFSEntry model - Normalized representation of a single DFS contest entry.

Uses Pydantic v2 for validation. All money fields use Decimal for precision.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal


class DFSEntry(BaseModel):
    """
    Normalized DFS contest entry from DraftKings or FanDuel.
    Why: Single data structure for both platforms enables unified analysis.
    """
    entry_id: str
    date: datetime
    sport: str  # Uppercase: NFL, NBA, NHL, MLB, etc.
    contest_type: Literal["GPP", "CASH", "H2H", "MULTI", "UNKNOWN"]
    entry_fee: Decimal = Field(ge=0)  # Must be non-negative
    winnings: Decimal = Field(ge=0)
    points: Decimal
    source: Literal["DK", "FD"]
    contest_name: str | None = None

    model_config = {"frozen": False, "str_strip_whitespace": True}

    @field_validator('entry_fee', 'winnings', mode='before')
    @classmethod
    def validate_money(cls, v):
        """Ensure Decimal precision for money - convert if needed"""
        if isinstance(v, float):
            return Decimal(str(v))
        if isinstance(v, (int, str)):
            return Decimal(str(v))
        return v

    @field_validator('sport', mode='after')
    @classmethod
    def normalize_sport(cls, v: str) -> str:
        """Normalize sport to uppercase"""
        return v.upper()

    @property
    def roi(self) -> Decimal:
        """Return on investment percentage"""
        if self.entry_fee == 0:
            return Decimal('0')
        return ((self.winnings - self.entry_fee) / self.entry_fee) * 100

    @property
    def profit(self) -> Decimal:
        """Net profit/loss"""
        return self.winnings - self.entry_fee

    @property
    def is_profitable(self) -> bool:
        """Did this entry win money?"""
        return self.profit > 0
