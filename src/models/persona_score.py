"""
PersonaScore model - Confidence scores for persona archetypes.

This model represents the calculated fit scores for each of the three
persona archetypes: Bettor, Fantasy Player, and Stats Nerd.
Scores are normalized to sum to 1.0.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any


# Threshold for considering a persona score as "significant" for hybrid detection
HYBRID_THRESHOLD = Decimal('0.3')


@dataclass
class PersonaScore:
    """
    Confidence scores for each persona archetype.

    All scores are in the 0.0-1.0 range and must sum to 1.0 (normalized).
    This ensures scores represent relative confidence, not absolute values.

    Attributes:
        bettor: Confidence score for Bettor persona (tournament grinder)
        fantasy: Confidence score for Fantasy persona (optimizer)
        stats_nerd: Confidence score for Stats Nerd persona (researcher)

    Properties:
        primary_persona: The persona with highest score
        is_hybrid: True if multiple personas exceed 0.3 threshold
        confidence: Spread between highest and lowest scores (0-1)
    """

    bettor: Decimal
    fantasy: Decimal
    stats_nerd: Decimal

    def __post_init__(self) -> None:
        """
        Validate scores after initialization.

        Raises:
            ValueError: If any score is outside 0-1 range
            ValueError: If scores don't sum to 1.0 (within tolerance)
        """
        # Validate each score is in 0-1 range
        for name, score in [
            ('bettor', self.bettor),
            ('fantasy', self.fantasy),
            ('stats_nerd', self.stats_nerd),
        ]:
            if score < Decimal('0') or score > Decimal('1'):
                raise ValueError(
                    f"{name} score must be between 0 and 1, got: {score}"
                )

        # Validate scores sum to 1.0 (with small tolerance for rounding)
        total = self.bettor + self.fantasy + self.stats_nerd
        tolerance = Decimal('0.001')
        if abs(total - Decimal('1')) > tolerance:
            raise ValueError(
                f"Persona scores must sum to 1.0, got: {total} "
                f"(bettor={self.bettor}, fantasy={self.fantasy}, "
                f"stats_nerd={self.stats_nerd})"
            )

    @property
    def primary_persona(self) -> str:
        """
        Get the persona with the highest confidence score.

        Returns:
            'BETTOR', 'FANTASY', or 'STATS_NERD'
        """
        scores = {
            'BETTOR': self.bettor,
            'FANTASY': self.fantasy,
            'STATS_NERD': self.stats_nerd,
        }
        return max(scores, key=scores.get)

    @property
    def is_hybrid(self) -> bool:
        """
        Check if user exhibits multiple persona traits.

        A user is considered hybrid if 2+ personas exceed the
        HYBRID_THRESHOLD (0.3). This indicates mixed behavior patterns
        that don't fit cleanly into one archetype.

        Returns:
            True if 2+ scores exceed 0.3, False otherwise
        """
        high_scores = sum(
            1 for s in [self.bettor, self.fantasy, self.stats_nerd]
            if s > HYBRID_THRESHOLD
        )
        return high_scores >= 2

    @property
    def confidence(self) -> Decimal:
        """
        Calculate confidence in the primary persona assignment.

        Higher spread between max and min scores indicates more
        confidence in the classification. A spread of 0 means all
        personas are equally likely; spread of ~0.67 means one
        persona is dominant.

        Returns:
            Spread between highest and lowest score (0-1 range)
        """
        scores = [self.bettor, self.fantasy, self.stats_nerd]
        return max(scores) - min(scores)

    @property
    def secondary_persona(self) -> str:
        """
        Get the persona with the second-highest score.

        Returns:
            'BETTOR', 'FANTASY', or 'STATS_NERD'
        """
        scores = [
            ('BETTOR', self.bettor),
            ('FANTASY', self.fantasy),
            ('STATS_NERD', self.stats_nerd),
        ]
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
        return sorted_scores[1][0]

    @property
    def scores_ranked(self) -> list:
        """
        Get all personas ranked by score (highest first).

        Returns:
            List of (persona_name, score) tuples sorted descending
        """
        scores = [
            ('BETTOR', self.bettor),
            ('FANTASY', self.fantasy),
            ('STATS_NERD', self.stats_nerd),
        ]
        return sorted(scores, key=lambda x: x[1], reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize persona scores to dictionary.

        All Decimal values are converted to strings to preserve precision.
        Includes computed properties for convenience.

        Returns:
            Dictionary representation of persona scores
        """
        return {
            'bettor': str(self.bettor),
            'fantasy': str(self.fantasy),
            'stats_nerd': str(self.stats_nerd),
            'primary_persona': self.primary_persona,
            'is_hybrid': self.is_hybrid,
            'confidence': str(self.confidence),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonaScore':
        """
        Create PersonaScore from dictionary.

        Args:
            data: Dictionary with score fields

        Returns:
            New PersonaScore instance
        """
        return cls(
            bettor=Decimal(str(data['bettor'])),
            fantasy=Decimal(str(data['fantasy'])),
            stats_nerd=Decimal(str(data['stats_nerd'])),
        )

    @classmethod
    def from_raw_scores(
        cls,
        bettor_raw: float,
        fantasy_raw: float,
        stats_nerd_raw: float
    ) -> 'PersonaScore':
        """
        Create normalized PersonaScore from raw (unnormalized) scores.

        Raw scores can be any non-negative values. They will be
        normalized to sum to 1.0.

        Args:
            bettor_raw: Raw bettor score (any non-negative value)
            fantasy_raw: Raw fantasy score (any non-negative value)
            stats_nerd_raw: Raw stats_nerd score (any non-negative value)

        Returns:
            New PersonaScore with normalized scores summing to 1.0

        Raises:
            ValueError: If all scores are zero
        """
        total = bettor_raw + fantasy_raw + stats_nerd_raw

        if total == 0:
            # Edge case: all zeros - return equal distribution
            return cls(
                bettor=Decimal('0.33'),
                fantasy=Decimal('0.33'),
                stats_nerd=Decimal('0.34'),
            )

        # Normalize to sum to 1.0
        bettor_norm = Decimal(str(bettor_raw / total))
        fantasy_norm = Decimal(str(fantasy_raw / total))
        stats_nerd_norm = Decimal(str(stats_nerd_raw / total))

        # Round to 3 decimal places
        bettor_norm = bettor_norm.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        fantasy_norm = fantasy_norm.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

        # Ensure sum is exactly 1.0 by adjusting stats_nerd
        stats_nerd_norm = Decimal('1') - bettor_norm - fantasy_norm

        return cls(
            bettor=bettor_norm,
            fantasy=fantasy_norm,
            stats_nerd=stats_nerd_norm,
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"PersonaScore("
            f"primary={self.primary_persona}, "
            f"bettor={self.bettor:.1%}, "
            f"fantasy={self.fantasy:.1%}, "
            f"stats_nerd={self.stats_nerd:.1%}, "
            f"hybrid={self.is_hybrid})"
        )
