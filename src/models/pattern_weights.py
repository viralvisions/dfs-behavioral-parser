"""
PatternWeights model - Multipliers for pattern detection algorithms.

This model represents personalized weights for different pattern detection
categories, used to prioritize certain insights based on user persona.
"""

from dataclasses import dataclass, field, fields
from decimal import Decimal
from typing import Dict, Any, List


# List of all pattern names (used for iteration)
PATTERN_NAMES: List[str] = [
    'line_movement',
    'historical_trends',
    'injury_impact',
    'weather_factors',
    'player_correlations',
    'situational_stats',
    'live_odds_delta',
    'contrarian_plays',
]


@dataclass
class PatternWeights:
    """
    Multipliers for pattern detection algorithms.

    Each weight adjusts the importance of a specific pattern category
    when generating insights. Weights default to 1.0 (neutral) and
    can be adjusted up (prioritize) or down (deprioritize) based on
    user persona.

    Attributes:
        line_movement: Betting line shifts (Bettor priority)
        historical_trends: Long-term statistical patterns (Stats Nerd)
        injury_impact: News-driven lineup changes (Fantasy priority)
        weather_factors: Environmental variables (Stats Nerd)
        player_correlations: Stacking strategies (Fantasy priority)
        situational_stats: Context-specific performance (Stats Nerd)
        live_odds_delta: Real-time line shopping (Bettor priority)
        contrarian_plays: Low-ownership opportunities (Fantasy/Stats)

    Methods:
        apply_to_score: Apply weight multiplier to a base score
        to_dict: Serialize to dictionary
        from_dict: Create from dictionary
    """

    line_movement: Decimal = field(default_factory=lambda: Decimal('1.0'))
    historical_trends: Decimal = field(default_factory=lambda: Decimal('1.0'))
    injury_impact: Decimal = field(default_factory=lambda: Decimal('1.0'))
    weather_factors: Decimal = field(default_factory=lambda: Decimal('1.0'))
    player_correlations: Decimal = field(default_factory=lambda: Decimal('1.0'))
    situational_stats: Decimal = field(default_factory=lambda: Decimal('1.0'))
    live_odds_delta: Decimal = field(default_factory=lambda: Decimal('1.0'))
    contrarian_plays: Decimal = field(default_factory=lambda: Decimal('1.0'))

    def __post_init__(self) -> None:
        """
        Validate weights after initialization.

        Raises:
            ValueError: If any weight is negative
        """
        for field_obj in fields(self):
            value = getattr(self, field_obj.name)
            if value < Decimal('0'):
                raise ValueError(
                    f"Weight '{field_obj.name}' cannot be negative: {value}"
                )

    def apply_to_score(self, pattern_name: str, base_score: Decimal) -> Decimal:
        """
        Apply weight multiplier to a base pattern score.

        Args:
            pattern_name: Name of the pattern (must match a weight field)
            base_score: The base score to multiply

        Returns:
            Weighted score (base_score * weight)

        Raises:
            AttributeError: If pattern_name doesn't match a weight field
        """
        weight = getattr(self, pattern_name)
        return base_score * weight

    def get_weight(self, pattern_name: str) -> Decimal:
        """
        Get weight for a specific pattern.

        Args:
            pattern_name: Name of the pattern

        Returns:
            Weight value for the pattern

        Raises:
            AttributeError: If pattern_name doesn't match a weight field
        """
        return getattr(self, pattern_name)

    @property
    def weights_ranked(self) -> List[tuple]:
        """
        Get all weights ranked by value (highest first).

        Returns:
            List of (pattern_name, weight) tuples sorted descending
        """
        weights = [
            (name, getattr(self, name))
            for name in PATTERN_NAMES
        ]
        return sorted(weights, key=lambda x: x[1], reverse=True)

    @property
    def top_patterns(self) -> List[str]:
        """
        Get pattern names with weight > 1.0 (prioritized).

        Returns:
            List of pattern names sorted by weight descending
        """
        return [
            name for name, weight in self.weights_ranked
            if weight > Decimal('1.0')
        ]

    @property
    def deprioritized_patterns(self) -> List[str]:
        """
        Get pattern names with weight < 1.0.

        Returns:
            List of pattern names sorted by weight ascending
        """
        patterns = [
            (name, weight) for name, weight in self.weights_ranked
            if weight < Decimal('1.0')
        ]
        return [name for name, _ in sorted(patterns, key=lambda x: x[1])]

    def to_dict(self) -> Dict[str, str]:
        """
        Serialize weights to dictionary.

        All Decimal values are converted to strings to preserve precision.

        Returns:
            Dictionary mapping pattern names to weight strings
        """
        return {
            name: str(getattr(self, name))
            for name in PATTERN_NAMES
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatternWeights':
        """
        Create PatternWeights from dictionary.

        Args:
            data: Dictionary mapping pattern names to weights

        Returns:
            New PatternWeights instance
        """
        return cls(**{
            name: Decimal(str(data.get(name, '1.0')))
            for name in PATTERN_NAMES
        })

    @classmethod
    def neutral(cls) -> 'PatternWeights':
        """
        Create PatternWeights with all weights at 1.0 (neutral).

        Returns:
            PatternWeights with default neutral weights
        """
        return cls()

    def __str__(self) -> str:
        """Human-readable string representation."""
        top = self.top_patterns[:3]
        top_str = ', '.join(f"{p}={getattr(self, p):.2f}x" for p in top)
        return f"PatternWeights(top=[{top_str}])"

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        weights_str = ', '.join(
            f"{name}={getattr(self, name)}"
            for name in PATTERN_NAMES
        )
        return f"PatternWeights({weights_str})"
