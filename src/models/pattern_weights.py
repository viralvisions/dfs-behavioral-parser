"""
PatternWeights model - Multipliers for pattern detection algorithms.

Uses Pydantic v2 for validation. All weights default to 1.0.
"""

from decimal import Decimal
from typing import List
from pydantic import BaseModel, Field, field_validator


# List of all pattern names for iteration
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


class PatternWeights(BaseModel):
    """
    Multipliers for pattern detection algorithms.
    Why: Bettor cares about line movement, Stats Nerd wants correlations.
    """
    line_movement: Decimal = Field(default=Decimal('1.0'), ge=0)
    historical_trends: Decimal = Field(default=Decimal('1.0'), ge=0)
    injury_impact: Decimal = Field(default=Decimal('1.0'), ge=0)
    weather_factors: Decimal = Field(default=Decimal('1.0'), ge=0)
    player_correlations: Decimal = Field(default=Decimal('1.0'), ge=0)
    situational_stats: Decimal = Field(default=Decimal('1.0'), ge=0)
    live_odds_delta: Decimal = Field(default=Decimal('1.0'), ge=0)
    contrarian_plays: Decimal = Field(default=Decimal('1.0'), ge=0)

    model_config = {"frozen": False}

    @field_validator('line_movement', 'historical_trends', 'injury_impact',
                     'weather_factors', 'player_correlations', 'situational_stats',
                     'live_odds_delta', 'contrarian_plays', mode='before')
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert to Decimal if needed"""
        if isinstance(v, (float, int, str)):
            return Decimal(str(v))
        return v

    def apply_to_pattern(self, pattern_value: Decimal, weight_key: str) -> Decimal:
        """Apply weight to a pattern value"""
        weight = getattr(self, weight_key, Decimal('1.0'))
        return pattern_value * weight

    @property
    def weights_ranked(self) -> List[tuple]:
        """Return weights sorted by value (highest first)"""
        weights_list = [(name, getattr(self, name)) for name in PATTERN_NAMES]
        return sorted(weights_list, key=lambda x: x[1], reverse=True)
