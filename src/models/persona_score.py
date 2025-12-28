"""
PersonaScore model - Confidence scores for persona archetypes.

Uses Pydantic v2 for validation. Scores are 0.0-1.0 range.
"""

from decimal import Decimal
from pydantic import BaseModel, field_validator, model_validator


class PersonaScore(BaseModel):
    """
    Confidence scores for each persona archetype.
    Why: Users often hybrid, need weighted blend not binary classification.
    """
    bettor: Decimal  # 0.0 to 1.0
    fantasy: Decimal
    stats_nerd: Decimal

    model_config = {"frozen": False}

    @field_validator('bettor', 'fantasy', 'stats_nerd', mode='before')
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert to Decimal if needed"""
        if isinstance(v, (float, int, str)):
            return Decimal(str(v))
        return v

    @field_validator('bettor', 'fantasy', 'stats_nerd', mode='after')
    @classmethod
    def validate_score(cls, v: Decimal) -> Decimal:
        """Scores must be 0.0-1.0"""
        if not (0 <= v <= 1):
            raise ValueError("Scores must be between 0.0 and 1.0")
        return v

    @property
    def primary_persona(self) -> str:
        """Return highest scoring persona"""
        scores = {
            'bettor': self.bettor,
            'fantasy': self.fantasy,
            'stats_nerd': self.stats_nerd
        }
        return max(scores, key=lambda k: scores[k])

    @property
    def is_hybrid(self) -> bool:
        """True if multiple personas > 0.3"""
        scores = [self.bettor, self.fantasy, self.stats_nerd]
        return sum(1 for s in scores if s > Decimal('0.3')) >= 2

    @property
    def confidence(self) -> Decimal:
        """Highest score value"""
        return max(self.bettor, self.fantasy, self.stats_nerd)

    @classmethod
    def from_raw_scores(
        cls,
        bettor_raw: float,
        fantasy_raw: float,
        stats_nerd_raw: float
    ) -> 'PersonaScore':
        """
        Create normalized PersonaScore from raw scores.
        Raw scores are normalized to sum to 1.0.
        """
        total = bettor_raw + fantasy_raw + stats_nerd_raw

        if total == 0:
            return cls(
                bettor=Decimal('0.33'),
                fantasy=Decimal('0.33'),
                stats_nerd=Decimal('0.34'),
            )

        return cls(
            bettor=Decimal(str(bettor_raw / total)),
            fantasy=Decimal(str(fantasy_raw / total)),
            stats_nerd=Decimal(str(stats_nerd_raw / total)),
        )
