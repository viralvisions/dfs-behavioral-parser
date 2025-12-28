"""
Unit tests for data models.

Tests cover:
- DFSEntry: validation, properties, serialization
- BehavioralMetrics: validation, properties, serialization
- PersonaScore: validation, properties, normalization
- PatternWeights: validation, methods, serialization
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.dfs_entry import DFSEntry
from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.models.pattern_weights import PatternWeights, PATTERN_NAMES


# =============================================================================
# DFSEntry Tests
# =============================================================================

class TestDFSEntry:
    """Tests for DFSEntry model."""

    def test_create_valid_entry(self):
        """Test creating a valid DFSEntry."""
        entry = DFSEntry(
            entry_id="12345",
            date=datetime(2024, 9, 15, 13, 0),
            sport="nfl",  # lowercase should be normalized
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('10.50'),
            points=Decimal('156.42'),
            source="DRAFTKINGS",
            contest_name="NFL $20K Shot"
        )

        assert entry.entry_id == "12345"
        assert entry.sport == "NFL"  # normalized to uppercase
        assert entry.source == "DRAFTKINGS"
        assert entry.entry_fee == Decimal('5.00')

    def test_sport_normalized_to_uppercase(self):
        """Test that sport is normalized to uppercase."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="nba",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('0'),
            points=Decimal('100'),
            source="FANDUEL"
        )
        assert entry.sport == "NBA"

    def test_source_normalized_to_uppercase(self):
        """Test that source is normalized to uppercase."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('0'),
            points=Decimal('100'),
            source="draftkings"  # lowercase
        )
        assert entry.source == "DRAFTKINGS"

    def test_reject_negative_entry_fee(self):
        """Test that negative entry_fee raises ValueError."""
        with pytest.raises(ValueError, match="Entry fee cannot be negative"):
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="GPP",
                entry_fee=Decimal('-5.00'),
                winnings=Decimal('0'),
                points=Decimal('100'),
                source="DRAFTKINGS"
            )

    def test_reject_negative_winnings(self):
        """Test that negative winnings raises ValueError."""
        with pytest.raises(ValueError, match="Winnings cannot be negative"):
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="GPP",
                entry_fee=Decimal('5.00'),
                winnings=Decimal('-10.00'),
                points=Decimal('100'),
                source="DRAFTKINGS"
            )

    def test_reject_invalid_source(self):
        """Test that invalid source raises ValueError."""
        with pytest.raises(ValueError, match="Invalid source"):
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="GPP",
                entry_fee=Decimal('5.00'),
                winnings=Decimal('0'),
                points=Decimal('100'),
                source="YAHOO"  # Invalid
            )

    def test_roi_calculation_winning(self):
        """Test ROI calculation for winning entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('10.00'),
            winnings=Decimal('25.00'),
            points=Decimal('150'),
            source="DRAFTKINGS"
        )
        # ROI = (25 - 10) / 10 * 100 = 150%
        assert entry.roi == Decimal('150.00')

    def test_roi_calculation_losing(self):
        """Test ROI calculation for losing entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('10.00'),
            winnings=Decimal('0'),
            points=Decimal('80'),
            source="DRAFTKINGS"
        )
        # ROI = (0 - 10) / 10 * 100 = -100%
        assert entry.roi == Decimal('-100.00')

    def test_roi_zero_entry_fee(self):
        """Test ROI with zero entry fee (freeroll)."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('0'),
            winnings=Decimal('5.00'),
            points=Decimal('100'),
            source="DRAFTKINGS"
        )
        # Should return 0 to avoid division by zero
        assert entry.roi == Decimal('0')

    def test_profit_calculation(self):
        """Test profit calculation."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('10.50'),
            points=Decimal('150'),
            source="DRAFTKINGS"
        )
        assert entry.profit == Decimal('5.50')

    def test_is_winning_entry_true(self):
        """Test is_winning_entry for profitable entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('10.00'),
            points=Decimal('150'),
            source="DRAFTKINGS"
        )
        assert entry.is_winning_entry is True

    def test_is_winning_entry_false(self):
        """Test is_winning_entry for losing entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('0'),
            points=Decimal('80'),
            source="DRAFTKINGS"
        )
        assert entry.is_winning_entry is False

    def test_is_winning_entry_breakeven(self):
        """Test is_winning_entry for break-even entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('5.00'),
            points=Decimal('100'),
            source="DRAFTKINGS"
        )
        # Break-even is not "winning"
        assert entry.is_winning_entry is False

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        entry = DFSEntry(
            entry_id="12345",
            date=datetime(2024, 9, 15, 13, 0),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('10.50'),
            points=Decimal('156.42'),
            source="DRAFTKINGS",
            contest_name="NFL $20K Shot"
        )

        data = entry.to_dict()

        assert data['entry_id'] == "12345"
        assert data['sport'] == "NFL"
        assert data['entry_fee'] == "5.00"
        assert data['winnings'] == "10.50"
        assert Decimal(data['roi']) == Decimal('110')  # (10.50 - 5.00) / 5.00 * 100
        assert data['profit'] == "5.50"
        assert data['is_winning_entry'] is True
        assert data['contest_name'] == "NFL $20K Shot"

    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            'entry_id': "12345",
            'date': "2024-09-15T13:00:00",
            'sport': "NFL",
            'contest_type': "GPP",
            'entry_fee': "5.00",
            'winnings': "10.50",
            'points': "156.42",
            'source': "DRAFTKINGS",
            'contest_name': "NFL $20K Shot"
        }

        entry = DFSEntry.from_dict(data)

        assert entry.entry_id == "12345"
        assert entry.entry_fee == Decimal('5.00')
        assert entry.winnings == Decimal('10.50')

    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = DFSEntry(
            entry_id="12345",
            date=datetime(2024, 9, 15, 13, 0),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('10.50'),
            points=Decimal('156.42'),
            source="DRAFTKINGS",
            contest_name="NFL $20K Shot"
        )

        data = original.to_dict()
        restored = DFSEntry.from_dict(data)

        assert restored.entry_id == original.entry_id
        assert restored.entry_fee == original.entry_fee
        assert restored.winnings == original.winnings
        assert restored.sport == original.sport


# =============================================================================
# BehavioralMetrics Tests
# =============================================================================

class TestBehavioralMetrics:
    """Tests for BehavioralMetrics model."""

    @pytest.fixture
    def sample_metrics(self):
        """Create sample metrics for testing."""
        return BehavioralMetrics(
            total_entries=100,
            entries_by_sport={"NFL": 60, "NBA": 30, "NHL": 10},
            entries_by_contest_type={"GPP": 70, "CASH": 20, "H2H": 10},
            total_invested=Decimal('500.00'),
            total_winnings=Decimal('450.00'),
            avg_entry_fee=Decimal('5.00'),
            roi_overall=Decimal('-10.00'),
            gpp_percentage=Decimal('0.70'),
            cash_percentage=Decimal('0.20'),
            h2h_percentage=Decimal('0.10'),
            multi_entry_rate=Decimal('1.5'),
            sport_diversity=Decimal('0.65'),
            stake_variance=Decimal('0.40'),
            entries_per_week=Decimal('5.2'),
            most_active_day="Sunday",
            recency_score=Decimal('0.78'),
            confidence_score=Decimal('0.75')
        )

    def test_create_valid_metrics(self, sample_metrics):
        """Test creating valid BehavioralMetrics."""
        assert sample_metrics.total_entries == 100
        assert sample_metrics.gpp_percentage == Decimal('0.70')
        assert sample_metrics.confidence_score == Decimal('0.75')

    def test_reject_negative_total_entries(self):
        """Test that negative total_entries raises ValueError."""
        with pytest.raises(ValueError, match="total_entries cannot be negative"):
            BehavioralMetrics(
                total_entries=-1,
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
                most_active_day="",
                recency_score=Decimal('0'),
                confidence_score=Decimal('0'),
            )

    def test_reject_percentage_out_of_range(self):
        """Test that percentage > 1 raises ValueError."""
        with pytest.raises(ValueError, match="gpp_percentage must be between 0 and 1"):
            BehavioralMetrics(
                total_entries=10,
                entries_by_sport={},
                entries_by_contest_type={},
                total_invested=Decimal('0'),
                total_winnings=Decimal('0'),
                avg_entry_fee=Decimal('0'),
                roi_overall=Decimal('0'),
                gpp_percentage=Decimal('1.5'),  # Invalid
                cash_percentage=Decimal('0'),
                h2h_percentage=Decimal('0'),
                multi_entry_rate=Decimal('0'),
                sport_diversity=Decimal('0'),
                stake_variance=Decimal('0'),
                entries_per_week=Decimal('0'),
                most_active_day="",
                recency_score=Decimal('0'),
                confidence_score=Decimal('0'),
            )

    def test_net_profit_property(self, sample_metrics):
        """Test net_profit calculation."""
        # 450 - 500 = -50
        assert sample_metrics.net_profit == Decimal('-50.00')

    def test_is_profitable_false(self, sample_metrics):
        """Test is_profitable for losing user."""
        assert sample_metrics.is_profitable is False

    def test_is_profitable_true(self):
        """Test is_profitable for winning user."""
        metrics = BehavioralMetrics(
            total_entries=10,
            entries_by_sport={"NFL": 10},
            entries_by_contest_type={"GPP": 10},
            total_invested=Decimal('100.00'),
            total_winnings=Decimal('150.00'),
            avg_entry_fee=Decimal('10.00'),
            roi_overall=Decimal('50.00'),
            gpp_percentage=Decimal('1.0'),
            cash_percentage=Decimal('0'),
            h2h_percentage=Decimal('0'),
            multi_entry_rate=Decimal('1.0'),
            sport_diversity=Decimal('0'),
            stake_variance=Decimal('0'),
            entries_per_week=Decimal('5'),
            most_active_day="Sunday",
            recency_score=Decimal('0.9'),
            confidence_score=Decimal('0.5'),
        )
        assert metrics.is_profitable is True

    def test_primary_sport(self, sample_metrics):
        """Test primary_sport property."""
        assert sample_metrics.primary_sport == "NFL"

    def test_primary_contest_type(self, sample_metrics):
        """Test primary_contest_type property."""
        assert sample_metrics.primary_contest_type == "GPP"

    def test_empty_metrics_factory(self):
        """Test empty() factory method."""
        empty = BehavioralMetrics.empty()
        assert empty.total_entries == 0
        assert empty.total_invested == Decimal('0')
        assert empty.confidence_score == Decimal('0')

    def test_to_dict_serialization(self, sample_metrics):
        """Test serialization to dictionary."""
        data = sample_metrics.to_dict()

        assert data['total_entries'] == 100
        assert data['total_invested'] == "500.00"
        assert data['roi_overall'] == "-10.00"
        assert data['net_profit'] == "-50.00"
        assert data['is_profitable'] is False
        assert data['primary_sport'] == "NFL"

    def test_from_dict_deserialization(self, sample_metrics):
        """Test deserialization from dictionary."""
        data = sample_metrics.to_dict()
        restored = BehavioralMetrics.from_dict(data)

        assert restored.total_entries == sample_metrics.total_entries
        assert restored.total_invested == sample_metrics.total_invested
        assert restored.gpp_percentage == sample_metrics.gpp_percentage


# =============================================================================
# PersonaScore Tests
# =============================================================================

class TestPersonaScore:
    """Tests for PersonaScore model."""

    def test_create_valid_persona_score(self):
        """Test creating a valid PersonaScore."""
        score = PersonaScore(
            bettor=Decimal('0.50'),
            fantasy=Decimal('0.30'),
            stats_nerd=Decimal('0.20')
        )
        assert score.bettor == Decimal('0.50')
        assert score.fantasy == Decimal('0.30')
        assert score.stats_nerd == Decimal('0.20')

    def test_reject_score_below_zero(self):
        """Test that negative score raises ValueError."""
        with pytest.raises(ValueError, match="bettor score must be between 0 and 1"):
            PersonaScore(
                bettor=Decimal('-0.1'),
                fantasy=Decimal('0.6'),
                stats_nerd=Decimal('0.5')
            )

    def test_reject_score_above_one(self):
        """Test that score > 1 raises ValueError."""
        with pytest.raises(ValueError, match="fantasy score must be between 0 and 1"):
            PersonaScore(
                bettor=Decimal('0.2'),
                fantasy=Decimal('1.5'),
                stats_nerd=Decimal('0.3')
            )

    def test_reject_scores_not_summing_to_one(self):
        """Test that scores not summing to 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Persona scores must sum to 1.0"):
            PersonaScore(
                bettor=Decimal('0.50'),
                fantasy=Decimal('0.30'),
                stats_nerd=Decimal('0.30')  # Sum = 1.1
            )

    def test_primary_persona_bettor(self):
        """Test primary_persona when bettor is highest."""
        score = PersonaScore(
            bettor=Decimal('0.60'),
            fantasy=Decimal('0.25'),
            stats_nerd=Decimal('0.15')
        )
        assert score.primary_persona == "BETTOR"

    def test_primary_persona_fantasy(self):
        """Test primary_persona when fantasy is highest."""
        score = PersonaScore(
            bettor=Decimal('0.20'),
            fantasy=Decimal('0.55'),
            stats_nerd=Decimal('0.25')
        )
        assert score.primary_persona == "FANTASY"

    def test_primary_persona_stats_nerd(self):
        """Test primary_persona when stats_nerd is highest."""
        score = PersonaScore(
            bettor=Decimal('0.15'),
            fantasy=Decimal('0.25'),
            stats_nerd=Decimal('0.60')
        )
        assert score.primary_persona == "STATS_NERD"

    def test_is_hybrid_true(self):
        """Test is_hybrid when multiple personas > 0.3."""
        score = PersonaScore(
            bettor=Decimal('0.45'),
            fantasy=Decimal('0.40'),
            stats_nerd=Decimal('0.15')
        )
        assert score.is_hybrid is True

    def test_is_hybrid_false(self):
        """Test is_hybrid when only one persona > 0.3."""
        score = PersonaScore(
            bettor=Decimal('0.70'),
            fantasy=Decimal('0.20'),
            stats_nerd=Decimal('0.10')
        )
        assert score.is_hybrid is False

    def test_confidence_high(self):
        """Test confidence for clear persona."""
        score = PersonaScore(
            bettor=Decimal('0.80'),
            fantasy=Decimal('0.15'),
            stats_nerd=Decimal('0.05')
        )
        # 0.80 - 0.05 = 0.75
        assert score.confidence == Decimal('0.75')

    def test_confidence_low(self):
        """Test confidence for unclear persona."""
        score = PersonaScore(
            bettor=Decimal('0.35'),
            fantasy=Decimal('0.33'),
            stats_nerd=Decimal('0.32')
        )
        # 0.35 - 0.32 = 0.03
        assert score.confidence == Decimal('0.03')

    def test_secondary_persona(self):
        """Test secondary_persona property."""
        score = PersonaScore(
            bettor=Decimal('0.60'),
            fantasy=Decimal('0.25'),
            stats_nerd=Decimal('0.15')
        )
        assert score.secondary_persona == "FANTASY"

    def test_scores_ranked(self):
        """Test scores_ranked property."""
        score = PersonaScore(
            bettor=Decimal('0.15'),
            fantasy=Decimal('0.60'),
            stats_nerd=Decimal('0.25')
        )
        ranked = score.scores_ranked
        assert ranked[0] == ('FANTASY', Decimal('0.60'))
        assert ranked[1] == ('STATS_NERD', Decimal('0.25'))
        assert ranked[2] == ('BETTOR', Decimal('0.15'))

    def test_from_raw_scores_normalization(self):
        """Test from_raw_scores normalizes correctly."""
        score = PersonaScore.from_raw_scores(
            bettor_raw=2.0,
            fantasy_raw=1.0,
            stats_nerd_raw=1.0
        )
        # Total = 4.0, so bettor = 0.5, fantasy = 0.25, stats = 0.25
        assert score.bettor == Decimal('0.5')
        assert score.fantasy == Decimal('0.25')
        assert score.stats_nerd == Decimal('0.25')

    def test_from_raw_scores_all_zeros(self):
        """Test from_raw_scores handles all zeros."""
        score = PersonaScore.from_raw_scores(
            bettor_raw=0.0,
            fantasy_raw=0.0,
            stats_nerd_raw=0.0
        )
        # Should return equal distribution
        assert score.bettor == Decimal('0.33')
        assert score.fantasy == Decimal('0.33')
        assert score.stats_nerd == Decimal('0.34')

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        score = PersonaScore(
            bettor=Decimal('0.50'),
            fantasy=Decimal('0.30'),
            stats_nerd=Decimal('0.20')
        )
        data = score.to_dict()

        assert data['bettor'] == '0.50'
        assert data['fantasy'] == '0.30'
        assert data['stats_nerd'] == '0.20'
        assert data['primary_persona'] == 'BETTOR'
        assert data['is_hybrid'] is False

    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            'bettor': '0.50',
            'fantasy': '0.30',
            'stats_nerd': '0.20'
        }
        score = PersonaScore.from_dict(data)

        assert score.bettor == Decimal('0.50')
        assert score.fantasy == Decimal('0.30')


# =============================================================================
# PatternWeights Tests
# =============================================================================

class TestPatternWeights:
    """Tests for PatternWeights model."""

    def test_create_default_weights(self):
        """Test creating PatternWeights with defaults."""
        weights = PatternWeights()

        for name in PATTERN_NAMES:
            assert getattr(weights, name) == Decimal('1.0')

    def test_create_custom_weights(self):
        """Test creating PatternWeights with custom values."""
        weights = PatternWeights(
            line_movement=Decimal('1.5'),
            historical_trends=Decimal('0.8')
        )
        assert weights.line_movement == Decimal('1.5')
        assert weights.historical_trends == Decimal('0.8')
        assert weights.injury_impact == Decimal('1.0')  # default

    def test_reject_negative_weights(self):
        """Test that negative weight raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            PatternWeights(line_movement=Decimal('-0.5'))

    def test_apply_to_score(self):
        """Test apply_to_score method."""
        weights = PatternWeights(line_movement=Decimal('1.5'))
        base_score = Decimal('0.80')
        weighted = weights.apply_to_score('line_movement', base_score)
        assert weighted == Decimal('1.20')

    def test_get_weight(self):
        """Test get_weight method."""
        weights = PatternWeights(situational_stats=Decimal('1.6'))
        assert weights.get_weight('situational_stats') == Decimal('1.6')
        assert weights.get_weight('line_movement') == Decimal('1.0')

    def test_weights_ranked(self):
        """Test weights_ranked property."""
        weights = PatternWeights(
            line_movement=Decimal('1.5'),
            historical_trends=Decimal('0.8'),
            injury_impact=Decimal('1.2')
        )
        ranked = weights.weights_ranked

        # First should be line_movement (1.5)
        assert ranked[0][0] == 'line_movement'
        assert ranked[0][1] == Decimal('1.5')

    def test_top_patterns(self):
        """Test top_patterns property."""
        weights = PatternWeights(
            line_movement=Decimal('1.5'),
            historical_trends=Decimal('0.8'),
            injury_impact=Decimal('1.2')
        )
        top = weights.top_patterns

        assert 'line_movement' in top
        assert 'injury_impact' in top
        assert 'historical_trends' not in top

    def test_deprioritized_patterns(self):
        """Test deprioritized_patterns property."""
        weights = PatternWeights(
            line_movement=Decimal('1.5'),
            historical_trends=Decimal('0.8'),
            live_odds_delta=Decimal('0.6')
        )
        deprioritized = weights.deprioritized_patterns

        assert 'historical_trends' in deprioritized
        assert 'live_odds_delta' in deprioritized
        assert 'line_movement' not in deprioritized

    def test_neutral_factory(self):
        """Test neutral() factory method."""
        weights = PatternWeights.neutral()
        for name in PATTERN_NAMES:
            assert getattr(weights, name) == Decimal('1.0')

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        weights = PatternWeights(
            line_movement=Decimal('1.5'),
            situational_stats=Decimal('1.6')
        )
        data = weights.to_dict()

        assert data['line_movement'] == '1.5'
        assert data['situational_stats'] == '1.6'
        assert data['injury_impact'] == '1.0'

    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            'line_movement': '1.5',
            'historical_trends': '1.3',
            'injury_impact': '1.0',
            'weather_factors': '1.0',
            'player_correlations': '1.0',
            'situational_stats': '1.6',
            'live_odds_delta': '0.8',
            'contrarian_plays': '1.1'
        }
        weights = PatternWeights.from_dict(data)

        assert weights.line_movement == Decimal('1.5')
        assert weights.situational_stats == Decimal('1.6')
        assert weights.live_odds_delta == Decimal('0.8')

    def test_from_dict_missing_keys(self):
        """Test from_dict with missing keys uses defaults."""
        data = {
            'line_movement': '1.5'
        }
        weights = PatternWeights.from_dict(data)

        assert weights.line_movement == Decimal('1.5')
        assert weights.historical_trends == Decimal('1.0')  # default

    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = PatternWeights(
            line_movement=Decimal('1.5'),
            situational_stats=Decimal('1.6'),
            live_odds_delta=Decimal('0.7')
        )

        data = original.to_dict()
        restored = PatternWeights.from_dict(data)

        assert restored.line_movement == original.line_movement
        assert restored.situational_stats == original.situational_stats
        assert restored.live_odds_delta == original.live_odds_delta
