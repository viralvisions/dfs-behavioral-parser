"""
Unit tests for scoring module.

Tests cover:
- Behavioral metrics calculation
- Persona detection
- Weight mapping
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.dfs_entry import DFSEntry
from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.scoring.behavioral_scorer import BehavioralScorer, calculate_metrics
from src.scoring.persona_detector import PersonaDetector, score_personas
from src.scoring.weight_mapper import WeightMapper, calculate_weights


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_entries():
    """Create a sample set of DFS entries for testing."""
    base_date = datetime(2024, 10, 1)

    return [
        DFSEntry(
            entry_id="1",
            date=base_date,
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('0.00'),
            points=Decimal('142.50'),
            source="DK",
            contest_name="NFL $20K GPP",
        ),
        DFSEntry(
            entry_id="2",
            date=base_date + timedelta(days=7),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('25.00'),
            winnings=Decimal('75.00'),
            points=Decimal('178.20'),
            source="DK",
            contest_name="NFL Sunday Million",
        ),
        DFSEntry(
            entry_id="3",
            date=base_date + timedelta(days=14),
            sport="NBA",
            contest_type="CASH",
            entry_fee=Decimal('3.00'),
            winnings=Decimal('5.40'),
            points=Decimal('245.80'),
            source="DK",
            contest_name="NBA 50/50",
        ),
        DFSEntry(
            entry_id="4",
            date=base_date + timedelta(days=21),
            sport="MLB",
            contest_type="H2H",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('9.00'),
            points=Decimal('312.10'),
            source="DK",
            contest_name="MLB H2H",
        ),
        DFSEntry(
            entry_id="5",
            date=base_date + timedelta(days=28),
            sport="NHL",
            contest_type="GPP",
            entry_fee=Decimal('10.00'),
            winnings=Decimal('0.00'),
            points=Decimal('42.50'),
            source="DK",
            contest_name="NHL $50K GTD",
        ),
    ]


@pytest.fixture
def bettor_entries():
    """Create entries that match Bettor profile."""
    base_date = datetime(2024, 10, 1)

    return [
        DFSEntry(
            entry_id=str(i),
            date=base_date + timedelta(days=i),
            sport="NFL",  # Focused on one sport
            contest_type="GPP",  # All GPPs
            entry_fee=Decimal('25.00'),  # Higher stakes
            winnings=Decimal('0.00'),
            points=Decimal('150.00'),
            source="DK",
            contest_name=f"NFL GPP {i}",
        )
        for i in range(10)
    ]


@pytest.fixture
def stats_nerd_entries():
    """Create entries that match Stats Nerd profile."""
    base_date = datetime(2024, 10, 1)
    sports = ["NFL", "NBA", "MLB", "NHL", "PGA"]

    entries = []
    for i, sport in enumerate(sports * 2):  # 10 entries, diverse sports
        entries.append(DFSEntry(
            entry_id=str(i),
            date=base_date + timedelta(days=i),
            sport=sport,
            contest_type=["GPP", "CASH", "H2H"][i % 3],
            entry_fee=Decimal(str((i % 5) + 1)),  # Varied stakes $1-$5
            winnings=Decimal('0.00'),
            points=Decimal('100.00'),
            source="DK",
            contest_name=f"{sport} Contest {i}",
        ))
    return entries


# =============================================================================
# BehavioralScorer Tests
# =============================================================================

class TestBehavioralScorer:
    """Tests for behavioral scoring."""

    def test_calculate_metrics_basic(self, sample_entries):
        """Test basic metrics calculation."""
        scorer = BehavioralScorer(reference_date=datetime(2024, 11, 1))
        metrics = scorer.calculate_metrics(sample_entries)

        assert metrics.total_entries == 5
        assert metrics.total_invested == Decimal('48.00')
        assert metrics.total_winnings == Decimal('89.40')

    def test_calculate_metrics_empty(self):
        """Test metrics for empty entry list."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics([])

        assert metrics.total_entries == 0
        assert metrics.total_invested == Decimal('0')
        assert metrics.recency_score == Decimal('0')

    def test_entries_by_sport(self, sample_entries):
        """Test sport counting."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        assert metrics.entries_by_sport["NFL"] == 2
        assert metrics.entries_by_sport["NBA"] == 1
        assert metrics.entries_by_sport["MLB"] == 1
        assert metrics.entries_by_sport["NHL"] == 1

    def test_entries_by_contest_type(self, sample_entries):
        """Test contest type counting."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        assert metrics.entries_by_contest_type["GPP"] == 3
        assert metrics.entries_by_contest_type["CASH"] == 1
        assert metrics.entries_by_contest_type["H2H"] == 1

    def test_roi_calculation(self, sample_entries):
        """Test ROI calculation."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        # ROI = (89.40 - 48.00) / 48.00 * 100 = 86.25%
        expected_roi = ((Decimal('89.40') - Decimal('48.00')) / Decimal('48.00')) * 100
        assert abs(metrics.roi_overall - expected_roi) < Decimal('0.01')

    def test_avg_entry_fee(self, sample_entries):
        """Test average entry fee calculation."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        # 48.00 / 5 = 9.60
        assert metrics.avg_entry_fee == Decimal('9.6')

    def test_gpp_percentage(self, sample_entries):
        """Test GPP percentage calculation."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        # 3 GPP out of 5 = 0.6
        assert float(metrics.gpp_percentage) == 0.6

    def test_sport_diversity_high(self, sample_entries):
        """Test high sport diversity (4 sports)."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        # 4 sports = high diversity
        assert float(metrics.sport_diversity) > 0.5

    def test_sport_diversity_low(self, bettor_entries):
        """Test low sport diversity (1 sport)."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(bettor_entries)

        # Only NFL = no diversity
        assert float(metrics.sport_diversity) == 0.0

    def test_recency_score_range(self, sample_entries):
        """Test recency score is in valid range."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        assert Decimal('0') <= metrics.recency_score <= Decimal('1')

    def test_most_active_day(self, sample_entries):
        """Test most active day calculation."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        # Should be a valid day name
        assert metrics.most_active_day in [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]

    def test_calculate_metrics_function(self, sample_entries):
        """Test convenience function."""
        metrics = calculate_metrics(sample_entries)
        assert metrics.total_entries == 5


# =============================================================================
# PersonaDetector Tests
# =============================================================================

class TestPersonaDetector:
    """Tests for persona detection."""

    def test_score_personas_returns_valid(self, sample_entries):
        """Test that persona scoring returns valid PersonaScore."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        # Scores should sum to 1.0
        total = persona_score.bettor + persona_score.fantasy + persona_score.stats_nerd
        assert abs(total - Decimal('1')) < Decimal('0.01')

    def test_bettor_profile_detected(self, bettor_entries):
        """Test that bettor-like entries score high for bettor."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(bettor_entries)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        # Bettor should have highest or second highest score
        # (Given high GPP%, high stakes, low diversity)
        assert persona_score.bettor > Decimal('0.25')

    def test_stats_nerd_profile_detected(self, stats_nerd_entries):
        """Test that stats-nerd-like entries score appropriately."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(stats_nerd_entries)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        # Stats nerd should have high score due to:
        # - High sport diversity
        # - Low stakes
        # - High stake variance
        assert persona_score.stats_nerd > Decimal('0.3')

    def test_primary_persona_assignment(self, sample_entries):
        """Test that primary persona is correctly assigned."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        # Primary should be the one with highest score
        primary = persona_score.primary_persona
        assert primary in ["bettor", "fantasy", "stats_nerd"]

        if primary == "bettor":
            assert persona_score.bettor >= persona_score.fantasy
            assert persona_score.bettor >= persona_score.stats_nerd

    def test_score_personas_function(self, sample_entries):
        """Test convenience function."""
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(sample_entries)

        persona_score = score_personas(metrics)
        assert isinstance(persona_score, PersonaScore)


# =============================================================================
# WeightMapper Tests
# =============================================================================

class TestWeightMapper:
    """Tests for weight mapping."""

    def test_calculate_weights_returns_valid(self):
        """Test that weight calculation returns valid PatternWeights."""
        persona_score = PersonaScore(
            bettor=Decimal('0.50'),
            fantasy=Decimal('0.30'),
            stats_nerd=Decimal('0.20')
        )

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # All weights should be positive
        assert weights.line_movement > Decimal('0')
        assert weights.situational_stats > Decimal('0')

    def test_pure_bettor_weights(self):
        """Test weights for pure bettor persona."""
        persona_score = PersonaScore(
            bettor=Decimal('0.90'),
            fantasy=Decimal('0.05'),
            stats_nerd=Decimal('0.05')
        )

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # Bettor priorities should be higher
        assert weights.line_movement > Decimal('1.3')
        assert weights.live_odds_delta > Decimal('1.2')

    def test_pure_stats_nerd_weights(self):
        """Test weights for pure stats nerd persona."""
        persona_score = PersonaScore(
            bettor=Decimal('0.05'),
            fantasy=Decimal('0.05'),
            stats_nerd=Decimal('0.90')
        )

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # Stats nerd priorities should be higher
        assert weights.situational_stats > Decimal('1.4')
        assert weights.historical_trends > Decimal('1.3')

    def test_hybrid_weights_blended(self):
        """Test that hybrid personas get blended weights."""
        persona_score = PersonaScore(
            bettor=Decimal('0.40'),
            fantasy=Decimal('0.40'),
            stats_nerd=Decimal('0.20')
        )

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # Weights should be moderate (blended)
        assert Decimal('0.7') < weights.line_movement < Decimal('1.5')
        assert Decimal('0.7') < weights.player_correlations < Decimal('1.5')

    def test_weights_ranked(self):
        """Test that weights can be ranked."""
        persona_score = PersonaScore(
            bettor=Decimal('0.10'),
            fantasy=Decimal('0.10'),
            stats_nerd=Decimal('0.80')
        )

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        ranked = weights.weights_ranked
        # First should be highest weight
        assert ranked[0][1] >= ranked[-1][1]

    def test_calculate_weights_function(self):
        """Test convenience function."""
        persona_score = PersonaScore(
            bettor=Decimal('0.33'),
            fantasy=Decimal('0.33'),
            stats_nerd=Decimal('0.34')
        )

        weights = calculate_weights(persona_score)
        assert weights is not None


# =============================================================================
# Integration Tests (Unit Level)
# =============================================================================

class TestScoringIntegration:
    """Integration tests for the full scoring pipeline."""

    def test_full_pipeline(self, sample_entries):
        """Test entries -> metrics -> persona -> weights pipeline."""
        # Step 1: Calculate metrics
        metrics = calculate_metrics(sample_entries)
        assert metrics.total_entries == 5

        # Step 2: Detect personas
        persona_score = score_personas(metrics)
        assert persona_score.primary_persona in ["bettor", "fantasy", "stats_nerd"]

        # Step 3: Calculate weights
        weights = calculate_weights(persona_score)
        assert weights.situational_stats > Decimal('0')

    def test_pipeline_different_profiles(self, bettor_entries, stats_nerd_entries):
        """Test that different profiles produce different weights."""
        # Bettor profile
        bettor_metrics = calculate_metrics(bettor_entries)
        bettor_persona = score_personas(bettor_metrics)
        bettor_weights = calculate_weights(bettor_persona)

        # Stats nerd profile
        nerd_metrics = calculate_metrics(stats_nerd_entries)
        nerd_persona = score_personas(nerd_metrics)
        nerd_weights = calculate_weights(nerd_persona)

        # Weights should differ
        assert bettor_weights.line_movement != nerd_weights.line_movement
        assert bettor_weights.situational_stats != nerd_weights.situational_stats
