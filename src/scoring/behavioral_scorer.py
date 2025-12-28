"""
Behavioral scorer for calculating metrics from DFS entry history.

Calculates 15+ behavioral metrics including volume, financial,
behavior patterns, temporal patterns, and confidence scoring.
"""

import math
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional

from src.models.dfs_entry import DFSEntry
from src.models.behavioral_metrics import BehavioralMetrics
from src.utils.constants import (
    RECENCY_HALF_LIFE_DAYS,
    CONFIDENCE_WEIGHT_VOLUME,
    CONFIDENCE_WEIGHT_RECENCY,
    CONFIDENCE_WEIGHT_DIVERSITY,
    MIN_ENTRIES_FOR_FULL_CONFIDENCE,
    STALE_DATA_THRESHOLD_DAYS,
)


class BehavioralScorer:
    """
    Calculator for behavioral metrics from entry history.

    Computes volume metrics, financial metrics, behavior patterns,
    temporal patterns, and data quality indicators.

    Example usage:
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(entries)
    """

    def __init__(self, reference_date: Optional[datetime] = None) -> None:
        """
        Initialize scorer.

        Args:
            reference_date: Date to use for recency calculations.
                          Defaults to current datetime.
        """
        self.reference_date = reference_date or datetime.now()

    def calculate_metrics(self, entries: List[DFSEntry]) -> BehavioralMetrics:
        """
        Calculate all behavioral metrics from entry history.

        Args:
            entries: List of DFSEntry objects

        Returns:
            BehavioralMetrics with all fields populated
        """
        if not entries:
            return BehavioralMetrics.empty()

        # Volume metrics
        total_entries = len(entries)
        entries_by_sport = self._count_by_sport(entries)
        entries_by_contest_type = self._count_by_contest_type(entries)

        # Financial metrics
        total_invested = sum(e.entry_fee for e in entries)
        total_winnings = sum(e.winnings for e in entries)
        avg_entry_fee = total_invested / Decimal(total_entries)
        roi_overall = self._calculate_roi(total_invested, total_winnings)

        # Behavior patterns
        gpp_percentage = self._calculate_type_percentage(entries, "GPP")
        cash_percentage = self._calculate_type_percentage(entries, "CASH")
        h2h_percentage = self._calculate_type_percentage(entries, "H2H")
        multi_entry_rate = self._calculate_multi_entry_rate(entries)
        sport_diversity = self._calculate_sport_diversity(entries)
        stake_variance = self._calculate_stake_variance(entries)

        # Temporal patterns
        entries_per_week = self._calculate_entries_per_week(entries)
        most_active_day = self._calculate_most_active_day(entries)
        recency_score = self._calculate_recency_score(entries)

        # Confidence score
        confidence_score = self._calculate_confidence(
            entries, entries_by_contest_type
        )

        return BehavioralMetrics(
            total_entries=total_entries,
            entries_by_sport=entries_by_sport,
            entries_by_contest_type=entries_by_contest_type,
            total_invested=total_invested,
            total_winnings=total_winnings,
            avg_entry_fee=avg_entry_fee,
            roi_overall=roi_overall,
            gpp_percentage=gpp_percentage,
            cash_percentage=cash_percentage,
            h2h_percentage=h2h_percentage,
            multi_entry_rate=multi_entry_rate,
            sport_diversity=sport_diversity,
            stake_variance=stake_variance,
            entries_per_week=entries_per_week,
            most_active_day=most_active_day,
            recency_score=recency_score,
            confidence_score=confidence_score,
        )

    def _count_by_sport(self, entries: List[DFSEntry]) -> Dict[str, int]:
        """Count entries by sport."""
        return dict(Counter(e.sport for e in entries))

    def _count_by_contest_type(self, entries: List[DFSEntry]) -> Dict[str, int]:
        """Count entries by contest type."""
        return dict(Counter(e.contest_type for e in entries))

    def _calculate_roi(
        self, invested: Decimal, winnings: Decimal
    ) -> Decimal:
        """
        Calculate return on investment percentage.

        Formula: ROI = ((winnings - invested) / invested) * 100
        """
        if invested == Decimal('0'):
            return Decimal('0')
        return ((winnings - invested) / invested) * Decimal('100')

    def _calculate_type_percentage(
        self, entries: List[DFSEntry], contest_type: str
    ) -> Decimal:
        """Calculate percentage of entries for a contest type."""
        count = sum(1 for e in entries if e.contest_type == contest_type)
        return Decimal(str(count / len(entries)))

    def _calculate_multi_entry_rate(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate average entries per unique contest.

        Higher rate indicates optimizer behavior (multiple lineups).
        """
        if not entries:
            return Decimal('0')

        # Group by contest name (approximate - same name = same contest)
        contest_counts = Counter(e.contest_name for e in entries)

        # Some entries might have None contest_name
        valid_counts = [c for name, c in contest_counts.items() if name]

        if not valid_counts:
            return Decimal('1')

        avg_entries_per_contest = sum(valid_counts) / len(valid_counts)
        return Decimal(str(avg_entries_per_contest))

    def _calculate_sport_diversity(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate sport diversity using Shannon entropy.

        Formula: H = -Σ(p_i * log2(p_i))
        Normalized to 0-1 range.

        Returns:
            0.0 = focused on one sport
            1.0 = evenly distributed across many sports
        """
        if not entries:
            return Decimal('0')

        sport_counts = Counter(e.sport for e in entries)
        total = len(entries)
        num_sports = len(sport_counts)

        if num_sports <= 1:
            return Decimal('0')

        # Calculate Shannon entropy
        entropy = 0.0
        for count in sport_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # Normalize to 0-1 range
        max_entropy = math.log2(num_sports)
        normalized = entropy / max_entropy if max_entropy > 0 else 0

        return Decimal(str(round(normalized, 4)))

    def _calculate_stake_variance(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate coefficient of variation for stakes.

        Formula: CV = std_dev / mean

        Higher CV indicates experimental betting behavior.
        """
        if len(entries) < 2:
            return Decimal('0')

        fees = [float(e.entry_fee) for e in entries]
        mean = sum(fees) / len(fees)

        if mean == 0:
            return Decimal('0')

        variance = sum((x - mean) ** 2 for x in fees) / len(fees)
        std_dev = math.sqrt(variance)

        cv = std_dev / mean
        return Decimal(str(round(cv, 4)))

    def _calculate_entries_per_week(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate average entries per week.

        Uses date range from first to last entry.
        """
        if not entries:
            return Decimal('0')

        dates = [e.date for e in entries]
        first_date = min(dates)
        last_date = max(dates)

        days_span = (last_date - first_date).days
        weeks = max(days_span / 7, 1)  # At least 1 week

        return Decimal(str(round(len(entries) / weeks, 2)))

    def _calculate_most_active_day(self, entries: List[DFSEntry]) -> str:
        """
        Determine the most active day of the week.

        Returns day name like "Sunday", "Monday", etc.
        """
        if not entries:
            return ""

        day_counts = Counter(e.date.strftime("%A") for e in entries)
        most_common = day_counts.most_common(1)

        return most_common[0][0] if most_common else ""

    def _calculate_recency_score(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate recency-weighted activity score.

        Uses exponential decay: weight = exp(-days_ago / half_life)

        Recent entries contribute more to the score.
        """
        if not entries:
            return Decimal('0')

        total_weight = 0.0
        for entry in entries:
            days_ago = (self.reference_date - entry.date).days
            # Clamp to non-negative (handle future dates)
            days_ago = max(0, days_ago)
            weight = math.exp(-days_ago / RECENCY_HALF_LIFE_DAYS)
            total_weight += weight

        # Normalize by number of entries
        max_possible = len(entries)  # All entries today would be 1.0 each
        normalized = total_weight / max_possible

        return Decimal(str(round(min(normalized, 1.0), 4)))

    def _calculate_confidence(
        self,
        entries: List[DFSEntry],
        entries_by_contest_type: Dict[str, int]
    ) -> Decimal:
        """
        Calculate confidence score for the metrics.

        Based on:
        - Volume: More entries = higher confidence
        - Recency: Recent data = higher confidence
        - Diversity: More contest types = higher confidence

        Returns value from 0.0 to 1.0.
        """
        if not entries:
            return Decimal('0')

        # Factor 1: Entry count (more = better)
        count_score = min(len(entries) / MIN_ENTRIES_FOR_FULL_CONFIDENCE, 1.0)

        # Factor 2: Recency (recent = better)
        most_recent = max(e.date for e in entries)
        days_old = (self.reference_date - most_recent).days
        recency_factor = max(0, 1.0 - (days_old / STALE_DATA_THRESHOLD_DAYS))

        # Factor 3: Contest diversity (varied = better)
        # 4 types maximum: GPP, CASH, H2H, MULTI
        unique_types = len([k for k in entries_by_contest_type if k != "UNKNOWN"])
        diversity_factor = min(unique_types / 4.0, 1.0)

        # Weighted average
        confidence = (
            float(CONFIDENCE_WEIGHT_VOLUME) * count_score +
            float(CONFIDENCE_WEIGHT_RECENCY) * recency_factor +
            float(CONFIDENCE_WEIGHT_DIVERSITY) * diversity_factor
        )

        return Decimal(str(round(confidence, 4)))


def calculate_metrics(entries: List[DFSEntry]) -> BehavioralMetrics:
    """
    Calculate behavioral metrics from entries.

    Convenience function using default scorer.

    Args:
        entries: List of DFSEntry objects

    Returns:
        BehavioralMetrics with all fields populated
    """
    scorer = BehavioralScorer()
    return scorer.calculate_metrics(entries)
