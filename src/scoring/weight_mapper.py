"""
Weight mapper for generating personalized pattern weights.

Blends persona-specific modifiers based on persona scores to create
personalized pattern detection weights.
"""

from decimal import Decimal
from typing import Dict

from src.models.persona_score import PersonaScore
from src.models.pattern_weights import PatternWeights, PATTERN_NAMES
from src.utils.constants import (
    BETTOR_MODIFIERS,
    FANTASY_MODIFIERS,
    STATS_NERD_MODIFIERS,
)


class WeightMapper:
    """
    Generator for personalized pattern weights.

    Blends modifier values from each persona based on the user's
    persona scores. Pure personas get their modifiers directly;
    hybrid personas get weighted blends.

    Example usage:
        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)
    """

    def calculate_weights(self, persona_scores: PersonaScore) -> PatternWeights:
        """
        Calculate personalized pattern weights from persona scores.

        Formula per pattern:
        weight = (bettor_score × bettor_modifier) +
                 (fantasy_score × fantasy_modifier) +
                 (stats_score × stats_modifier)

        Args:
            persona_scores: User's persona confidence scores

        Returns:
            PatternWeights with personalized multipliers
        """
        weights = {}

        for pattern_name in PATTERN_NAMES:
            bettor_mod = BETTOR_MODIFIERS[pattern_name]
            fantasy_mod = FANTASY_MODIFIERS[pattern_name]
            stats_mod = STATS_NERD_MODIFIERS[pattern_name]

            # Weighted blend
            final_weight = (
                persona_scores.bettor * bettor_mod +
                persona_scores.fantasy * fantasy_mod +
                persona_scores.stats_nerd * stats_mod
            )

            weights[pattern_name] = final_weight

        return PatternWeights(**weights)

    def get_weight_explanation(
        self,
        persona_scores: PersonaScore,
        weights: PatternWeights
    ) -> Dict[str, str]:
        """
        Generate explanations for weight values.

        Useful for debugging and user feedback.

        Args:
            persona_scores: User's persona scores
            weights: Calculated pattern weights

        Returns:
            Dict mapping pattern names to explanation strings
        """
        explanations = {}
        primary = persona_scores.primary_persona

        for pattern_name in PATTERN_NAMES:
            weight = getattr(weights, pattern_name)

            # Determine contribution source
            if weight > Decimal('1.1'):
                # Boosted
                if primary == "BETTOR":
                    explanations[pattern_name] = f"Boosted by Bettor persona ({weight:.2f}x)"
                elif primary == "FANTASY":
                    explanations[pattern_name] = f"Boosted by Fantasy persona ({weight:.2f}x)"
                else:
                    explanations[pattern_name] = f"Boosted by Stats Nerd persona ({weight:.2f}x)"
            elif weight < Decimal('0.9'):
                # Reduced
                explanations[pattern_name] = f"Deprioritized for your profile ({weight:.2f}x)"
            else:
                # Neutral
                explanations[pattern_name] = f"Neutral weight ({weight:.2f}x)"

        return explanations


def calculate_weights(persona_scores: PersonaScore) -> PatternWeights:
    """
    Calculate pattern weights from persona scores.

    Convenience function using default mapper.

    Args:
        persona_scores: User's persona scores

    Returns:
        PatternWeights with personalized multipliers
    """
    mapper = WeightMapper()
    return mapper.calculate_weights(persona_scores)
