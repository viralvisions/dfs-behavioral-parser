"""
BehavioralMetrics model - Aggregated metrics calculated from entry history.

Uses Pydantic v2 for validation. All percentages stored as Decimal 0.0-1.0.
"""

from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from typing import Dict


class BehavioralMetrics(BaseModel):
    """
    Aggregated metrics from entry history.
    Why: Single source of truth for persona detection.
    """
    # Volume metrics
    total_entries: int = Field(ge=0)
    entries_by_sport: Dict[str, int]
    entries_by_contest_type: Dict[str, int]

    # Financial metrics
    total_invested: Decimal = Field(ge=0)
    total_winnings: Decimal = Field(ge=0)
    avg_entry_fee: Decimal = Field(ge=0)
    roi_overall: Decimal

    # Behavior patterns (all 0.0 to 1.0)
    gpp_percentage: Decimal = Field(ge=0, le=1)
    cash_percentage: Decimal = Field(ge=0, le=1)
    multi_entry_rate: Decimal  # Avg entries per contest
    sport_diversity: Decimal = Field(ge=0, le=1)  # Shannon entropy normalized
    stake_variance: Decimal = Field(ge=0)  # Coefficient of variation

    # Temporal patterns
    entries_per_week: Decimal = Field(ge=0)
    most_active_day: str  # "Monday", "Tuesday", etc.
    recency_score: Decimal = Field(ge=0, le=1)  # 0.0 to 1.0, higher = more recent

    model_config = {"frozen": False}

    @field_validator('total_invested', 'total_winnings', 'avg_entry_fee', mode='before')
    @classmethod
    def validate_money(cls, v):
        """Convert to Decimal if needed"""
        if isinstance(v, (float, int, str)):
            return Decimal(str(v))
        return v

    @field_validator('gpp_percentage', 'cash_percentage', 'sport_diversity',
                     'stake_variance', 'multi_entry_rate', 'entries_per_week',
                     'recency_score', 'roi_overall', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v):
        """Convert to Decimal if needed"""
        if isinstance(v, (float, int, str)):
            return Decimal(str(v))
        return v

    @classmethod
    def empty(cls) -> 'BehavioralMetrics':
        """Create empty metrics for edge cases (no entries)"""
        return cls(
            total_entries=0,
            entries_by_sport={},
            entries_by_contest_type={},
            total_invested=Decimal('0'),
            total_winnings=Decimal('0'),
            avg_entry_fee=Decimal('0'),
            roi_overall=Decimal('0'),
            gpp_percentage=Decimal('0'),
            cash_percentage=Decimal('0'),
            multi_entry_rate=Decimal('1'),
            sport_diversity=Decimal('0'),
            stake_variance=Decimal('0'),
            entries_per_week=Decimal('0'),
            most_active_day='Unknown',
            recency_score=Decimal('0'),
        )
