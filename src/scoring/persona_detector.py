"""
Persona detector for scoring user archetypes.

Scores users against three persona types (Bettor, Fantasy, Stats Nerd)
based on their behavioral metrics.
"""

from decimal import Decimal
from typing import Dict, Tuple

from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.utils.constants import (
    BETTOR_SIGNALS,
    FANTASY_SIGNALS,
    STATS_NERD_SIGNALS,
)


class PersonaDetector:
    """
    Detector for user persona archetypes.

    Scores users against three personas:
    - BETTOR: Tournament grinder, higher stakes, focused
    - FANTASY: Optimizer, multi-entry, volume player
    - STATS_NERD: Researcher, diverse sports, experimental

    Example usage:
        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)
    """

    def score_personas(self, metrics: BehavioralMetrics) -> PersonaScore:
        """
        Score user against all persona archetypes.

        Args:
            metrics: Behavioral metrics calculated from entry history

        Returns:
            PersonaScore with normalized scores for each persona
        """
        # Calculate raw scores for each persona
        bettor_raw = self._score_bettor(metrics)
        fantasy_raw = self._score_fantasy(metrics)
        stats_nerd_raw = self._score_stats_nerd(metrics)

        # Normalize scores to sum to 1.0
        return PersonaScore.from_raw_scores(
            bettor_raw=bettor_raw,
            fantasy_raw=fantasy_raw,
            stats_nerd_raw=stats_nerd_raw,
        )

    def _score_bettor(self, metrics: BehavioralMetrics) -> float:
        """
        Score fit to Bettor persona.

        Signals:
        - High GPP percentage (0.7-1.0)
        - Higher avg stakes ($10+)
        - Low sport diversity (inverted: 0.0-0.5)
        - Low multi-entry rate (inverted: 1.0-2.0)
        """
        scores = []

        # GPP percentage: higher = more bettor-like
        scores.append(self._score_signal(
            float(metrics.gpp_percentage),
            BETTOR_SIGNALS['gpp_percentage']
        ))

        # Avg entry fee: higher = more bettor-like
        scores.append(self._score_signal(
            float(metrics.avg_entry_fee),
            BETTOR_SIGNALS['avg_entry_fee']
        ))

        # Sport diversity: LOWER = more bettor-like (inverted)
        diversity_score = self._score_signal(
            float(metrics.sport_diversity),
            BETTOR_SIGNALS['sport_diversity']
        )
        scores.append(1.0 - diversity_score)  # Invert

        # Multi-entry rate: LOWER = more bettor-like (inverted)
        multi_score = self._score_signal(
            float(metrics.multi_entry_rate),
            BETTOR_SIGNALS['multi_entry_rate']
        )
        scores.append(1.0 - multi_score)  # Invert

        return sum(scores) / len(scores) if scores else 0.0

    def _score_fantasy(self, metrics: BehavioralMetrics) -> float:
        """
        Score fit to Fantasy persona.

        Signals:
        - High cash percentage (0.4-1.0)
        - High multi-entry rate (3.0-20.0)
        - High volume (20+ entries/week)
        - Moderate ROI (-20% to +20%)
        """
        scores = []

        # Cash percentage: higher = more fantasy-like
        scores.append(self._score_signal(
            float(metrics.cash_percentage),
            FANTASY_SIGNALS['cash_percentage']
        ))

        # Multi-entry rate: higher = more fantasy-like
        scores.append(self._score_signal(
            float(metrics.multi_entry_rate),
            FANTASY_SIGNALS['multi_entry_rate']
        ))

        # Entries per week: higher = more fantasy-like
        scores.append(self._score_signal(
            float(metrics.entries_per_week),
            FANTASY_SIGNALS['entries_per_week']
        ))

        # Moderate ROI: closer to 0 = more fantasy-like
        # This is a special case - we want moderate, not extreme
        roi = float(metrics.roi_overall)
        roi_range = FANTASY_SIGNALS['roi_moderate']
        if roi_range[0] <= roi <= roi_range[1]:
            # Within moderate range, score based on closeness to 0
            max_deviation = max(abs(roi_range[0]), abs(roi_range[1]))
            roi_score = 1.0 - (abs(roi) / max_deviation)
        else:
            # Outside range
            roi_score = 0.0
        scores.append(roi_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _score_stats_nerd(self, metrics: BehavioralMetrics) -> float:
        """
        Score fit to Stats Nerd persona.

        Signals:
        - High sport diversity (0.7-1.0)
        - High stake variance (0.5+)
        - Lower avg stakes (inverted: $0-5)
        """
        scores = []

        # Sport diversity: higher = more stats nerd-like
        scores.append(self._score_signal(
            float(metrics.sport_diversity),
            STATS_NERD_SIGNALS['sport_diversity']
        ))

        # Stake variance: higher = more stats nerd-like
        scores.append(self._score_signal(
            float(metrics.stake_variance),
            STATS_NERD_SIGNALS['stake_variance']
        ))

        # Avg entry fee: LOWER = more stats nerd-like (inverted)
        fee_score = self._score_signal(
            float(metrics.avg_entry_fee),
            STATS_NERD_SIGNALS['avg_entry_fee']
        )
        scores.append(1.0 - fee_score)  # Invert: low stakes = high score

        return sum(scores) / len(scores) if scores else 0.0

    def _score_signal(
        self,
        value: float,
        signal_range: Tuple[float, float]
    ) -> float:
        """
        Score a value using linear interpolation within a range.

        Args:
            value: The metric value to score
            signal_range: Tuple of (min_value, max_value)

        Returns:
            Score from 0.0 to 1.0

        - Below min: 0.0
        - Above max: 1.0
        - Between: linear interpolation
        """
        min_val, max_val = signal_range

        if value < min_val:
            return 0.0
        elif value > max_val:
            return 1.0
        else:
            range_size = max_val - min_val
            if range_size == 0:
                return 1.0
            return (value - min_val) / range_size


def score_personas(metrics: BehavioralMetrics) -> PersonaScore:
    """
    Score personas for given metrics.

    Convenience function using default detector.

    Args:
        metrics: Behavioral metrics

    Returns:
        PersonaScore with normalized scores
    """
    detector = PersonaDetector()
    return detector.score_personas(metrics)
