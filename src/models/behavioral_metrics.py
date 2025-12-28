"""
BehavioralMetrics model - Aggregated metrics calculated from entry history.

This model captures 15+ behavioral signals calculated from a user's DFS
entry history, used for persona detection and pattern weight generation.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any


@dataclass
class BehavioralMetrics:
    """
    Aggregated behavioral metrics calculated from a user's entry history.

    Contains volume metrics, financial metrics, behavior patterns, temporal
    patterns, and data quality indicators. All percentage fields are
    normalized to 0.0-1.0 range.

    Volume Metrics:
        total_entries: Total number of entries analyzed
        entries_by_sport: Count of entries per sport
        entries_by_contest_type: Count of entries per contest type

    Financial Metrics:
        total_invested: Sum of all entry fees
        total_winnings: Sum of all winnings
        avg_entry_fee: Mean stake size
        roi_overall: Overall ROI percentage

    Behavior Patterns (0.0 to 1.0 scale):
        gpp_percentage: Fraction of entries in GPP tournaments
        cash_percentage: Fraction of entries in cash games
        h2h_percentage: Fraction of entries in head-to-head
        multi_entry_rate: Average entries per unique contest
        sport_diversity: Shannon entropy normalized (0=focused, 1=diverse)
        stake_variance: Coefficient of variation of stakes

    Temporal Patterns:
        entries_per_week: Average entries per week
        most_active_day: Day with most entries ("Sunday", etc.)
        recency_score: Exponential decay weighted score (0-1)

    Data Quality:
        confidence_score: Overall data quality indicator (0-1)
    """

    # Volume metrics
    total_entries: int
    entries_by_sport: Dict[str, int]
    entries_by_contest_type: Dict[str, int]

    # Financial metrics (all use Decimal for precision)
    total_invested: Decimal
    total_winnings: Decimal
    avg_entry_fee: Decimal
    roi_overall: Decimal

    # Behavior patterns (0.0 to 1.0 scale)
    gpp_percentage: Decimal
    cash_percentage: Decimal
    h2h_percentage: Decimal
    multi_entry_rate: Decimal
    sport_diversity: Decimal
    stake_variance: Decimal

    # Temporal patterns
    entries_per_week: Decimal
    most_active_day: str
    recency_score: Decimal

    # Data quality
    confidence_score: Decimal

    def __post_init__(self) -> None:
        """Validate metrics after initialization."""
        # Validate total_entries is non-negative
        if self.total_entries < 0:
            raise ValueError(
                f"total_entries cannot be negative: {self.total_entries}"
            )

        # Validate percentages are in 0-1 range
        percentage_fields = [
            ('gpp_percentage', self.gpp_percentage),
            ('cash_percentage', self.cash_percentage),
            ('h2h_percentage', self.h2h_percentage),
            ('sport_diversity', self.sport_diversity),
            ('confidence_score', self.confidence_score),
        ]

        for field_name, value in percentage_fields:
            if value < Decimal('0') or value > Decimal('1'):
                raise ValueError(
                    f"{field_name} must be between 0 and 1, got: {value}"
                )

    @property
    def net_profit(self) -> Decimal:
        """Calculate total net profit/loss."""
        return self.total_winnings - self.total_invested

    @property
    def is_profitable(self) -> bool:
        """Check if user is profitable overall."""
        return self.total_winnings > self.total_invested

    @property
    def win_rate(self) -> Decimal:
        """
        Estimate win rate based on ROI.

        This is an approximation since we don't track individual wins.
        Positive ROI suggests more wins than losses.
        """
        if self.roi_overall > Decimal('0'):
            return min(Decimal('1'), Decimal('0.5') + self.roi_overall / Decimal('200'))
        else:
            return max(Decimal('0'), Decimal('0.5') + self.roi_overall / Decimal('200'))

    @property
    def primary_sport(self) -> str:
        """Get the sport with most entries."""
        if not self.entries_by_sport:
            return "UNKNOWN"
        return max(self.entries_by_sport, key=self.entries_by_sport.get)

    @property
    def primary_contest_type(self) -> str:
        """Get the contest type with most entries."""
        if not self.entries_by_contest_type:
            return "UNKNOWN"
        return max(self.entries_by_contest_type, key=self.entries_by_contest_type.get)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize metrics to dictionary for JSON output.

        All Decimal values are converted to strings to preserve precision.

        Returns:
            Dictionary representation of the metrics
        """
        return {
            # Volume
            'total_entries': self.total_entries,
            'entries_by_sport': self.entries_by_sport.copy(),
            'entries_by_contest_type': self.entries_by_contest_type.copy(),

            # Financial
            'total_invested': str(self.total_invested),
            'total_winnings': str(self.total_winnings),
            'avg_entry_fee': str(self.avg_entry_fee),
            'roi_overall': str(self.roi_overall),
            'net_profit': str(self.net_profit),
            'is_profitable': self.is_profitable,

            # Behavior patterns
            'gpp_percentage': str(self.gpp_percentage),
            'cash_percentage': str(self.cash_percentage),
            'h2h_percentage': str(self.h2h_percentage),
            'multi_entry_rate': str(self.multi_entry_rate),
            'sport_diversity': str(self.sport_diversity),
            'stake_variance': str(self.stake_variance),

            # Temporal
            'entries_per_week': str(self.entries_per_week),
            'most_active_day': self.most_active_day,
            'recency_score': str(self.recency_score),

            # Quality
            'confidence_score': str(self.confidence_score),

            # Computed
            'primary_sport': self.primary_sport,
            'primary_contest_type': self.primary_contest_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BehavioralMetrics':
        """
        Create BehavioralMetrics from dictionary.

        Args:
            data: Dictionary with metrics fields

        Returns:
            New BehavioralMetrics instance
        """
        return cls(
            total_entries=data['total_entries'],
            entries_by_sport=data['entries_by_sport'].copy(),
            entries_by_contest_type=data['entries_by_contest_type'].copy(),
            total_invested=Decimal(str(data['total_invested'])),
            total_winnings=Decimal(str(data['total_winnings'])),
            avg_entry_fee=Decimal(str(data['avg_entry_fee'])),
            roi_overall=Decimal(str(data['roi_overall'])),
            gpp_percentage=Decimal(str(data['gpp_percentage'])),
            cash_percentage=Decimal(str(data['cash_percentage'])),
            h2h_percentage=Decimal(str(data['h2h_percentage'])),
            multi_entry_rate=Decimal(str(data['multi_entry_rate'])),
            sport_diversity=Decimal(str(data['sport_diversity'])),
            stake_variance=Decimal(str(data['stake_variance'])),
            entries_per_week=Decimal(str(data['entries_per_week'])),
            most_active_day=data['most_active_day'],
            recency_score=Decimal(str(data['recency_score'])),
            confidence_score=Decimal(str(data['confidence_score'])),
        )

    @classmethod
    def empty(cls) -> 'BehavioralMetrics':
        """
        Create an empty BehavioralMetrics for edge cases (no entries).

        Returns:
            BehavioralMetrics with zero/default values
        """
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
            h2h_percentage=Decimal('0'),
            multi_entry_rate=Decimal('0'),
            sport_diversity=Decimal('0'),
            stake_variance=Decimal('0'),
            entries_per_week=Decimal('0'),
            most_active_day='',
            recency_score=Decimal('0'),
            confidence_score=Decimal('0'),
        )
