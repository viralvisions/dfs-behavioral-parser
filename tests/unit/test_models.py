"""
Unit tests for data models.

Tests cover:
- DFSEntry: validation, properties, serialization
- BehavioralMetrics: validation, properties
- PersonaScore: validation, properties, normalization
- PatternWeights: validation, methods
- UserProfile: validation, nested models
"""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ValidationError

from src.models.dfs_entry import DFSEntry
from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.models.pattern_weights import PatternWeights
from src.models.user_profile import UserProfile


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
            source="DK",
            contest_name="NFL $20K Shot"
        )

        assert entry.entry_id == "12345"
        assert entry.sport == "NFL"  # normalized to uppercase
        assert entry.source == "DK"
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
            source="FD"
        )
        assert entry.sport == "NBA"

    def test_reject_negative_entry_fee(self):
        """Test that negative entry_fee raises ValidationError."""
        with pytest.raises(ValidationError):
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="GPP",
                entry_fee=Decimal('-5.00'),
                winnings=Decimal('0'),
                points=Decimal('100'),
                source="DK"
            )

    def test_reject_negative_winnings(self):
        """Test that negative winnings raises ValidationError."""
        with pytest.raises(ValidationError):
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="GPP",
                entry_fee=Decimal('5.00'),
                winnings=Decimal('-10.00'),
                points=Decimal('100'),
                source="DK"
            )

    def test_reject_invalid_source(self):
        """Test that invalid source raises ValidationError."""
        with pytest.raises(ValidationError):
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="GPP",
                entry_fee=Decimal('5.00'),
                winnings=Decimal('0'),
                points=Decimal('100'),
                source="YAHOO"  # Invalid - must be DK or FD
            )

    def test_reject_invalid_contest_type(self):
        """Test that invalid contest_type raises ValidationError."""
        with pytest.raises(ValidationError):
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="INVALID",
                entry_fee=Decimal('5.00'),
                winnings=Decimal('0'),
                points=Decimal('100'),
                source="DK"
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
            source="DK"
        )
        # ROI = (25 - 10) / 10 * 100 = 150%
        assert entry.roi == Decimal('150')

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
            source="DK"
        )
        # ROI = (0 - 10) / 10 * 100 = -100%
        assert entry.roi == Decimal('-100')

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
            source="DK"
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
            source="DK"
        )
        assert entry.profit == Decimal('5.50')

    def test_is_profitable_true(self):
        """Test is_profitable for profitable entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('10.00'),
            points=Decimal('150'),
            source="DK"
        )
        assert entry.is_profitable is True

    def test_is_profitable_false(self):
        """Test is_profitable for losing entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('0'),
            points=Decimal('80'),
            source="DK"
        )
        assert entry.is_profitable is False

    def test_is_profitable_breakeven(self):
        """Test is_profitable for break-even entry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('5.00'),
            points=Decimal('100'),
            source="DK"
        )
        # Break-even is not "profitable"
        assert entry.is_profitable is False

    def test_model_dump_serialization(self):
        """Test serialization to dictionary using model_dump."""
        entry = DFSEntry(
            entry_id="12345",
            date=datetime(2024, 9, 15, 13, 0),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('10.50'),
            points=Decimal('156.42'),
            source="DK",
            contest_name="NFL $20K Shot"
        )

        data = entry.model_dump()

        assert data['entry_id'] == "12345"
        assert data['sport'] == "NFL"
        assert data['source'] == "DK"

    def test_money_conversion_from_float(self):
        """Test that floats are converted to Decimal."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=5.00,  # float
            winnings=10.50,  # float
            points=Decimal('100'),
            source="DK"
        )
        assert isinstance(entry.entry_fee, Decimal)
        assert isinstance(entry.winnings, Decimal)

    def test_money_conversion_from_string(self):
        """Test that strings are converted to Decimal."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee="5.00",  # string
            winnings="10.50",  # string
            points=Decimal('100'),
            source="DK"
        )
        assert isinstance(entry.entry_fee, Decimal)
        assert entry.entry_fee == Decimal('5.00')


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
            multi_entry_rate=Decimal('1.5'),
            sport_diversity=Decimal('0.65'),
            stake_variance=Decimal('0.40'),
            entries_per_week=Decimal('5.2'),
            most_active_day="Sunday",
            recency_score=Decimal('0.78'),
        )

    def test_create_valid_metrics(self, sample_metrics):
        """Test creating valid BehavioralMetrics."""
        assert sample_metrics.total_entries == 100
        assert sample_metrics.gpp_percentage == Decimal('0.70')

    def test_reject_negative_total_entries(self):
        """Test that negative total_entries raises ValidationError."""
        with pytest.raises(ValidationError):
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
                multi_entry_rate=Decimal('0'),
                sport_diversity=Decimal('0'),
                stake_variance=Decimal('0'),
                entries_per_week=Decimal('0'),
                most_active_day="",
                recency_score=Decimal('0'),
            )

    def test_reject_percentage_out_of_range(self):
        """Test that percentage > 1 raises ValidationError."""
        with pytest.raises(ValidationError):
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
                multi_entry_rate=Decimal('0'),
                sport_diversity=Decimal('0'),
                stake_variance=Decimal('0'),
                entries_per_week=Decimal('0'),
                most_active_day="",
                recency_score=Decimal('0'),
            )

    def test_empty_metrics_factory(self):
        """Test empty() factory method."""
        empty = BehavioralMetrics.empty()
        assert empty.total_entries == 0
        assert empty.total_invested == Decimal('0')

    def test_decimal_conversion(self):
        """Test that numeric values are converted to Decimal."""
        metrics = BehavioralMetrics(
            total_entries=10,
            entries_by_sport={"NFL": 10},
            entries_by_contest_type={"GPP": 10},
            total_invested=100.0,  # float
            total_winnings="150.00",  # string
            avg_entry_fee=10,  # int
            roi_overall=50.0,
            gpp_percentage=1.0,
            cash_percentage=0,
            multi_entry_rate=1.0,
            sport_diversity=0,
            stake_variance=0,
            entries_per_week=5,
            most_active_day="Sunday",
            recency_score=0.9,
        )
        assert isinstance(metrics.total_invested, Decimal)
        assert isinstance(metrics.total_winnings, Decimal)


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
        """Test that negative score raises ValidationError."""
        with pytest.raises(ValidationError):
            PersonaScore(
                bettor=Decimal('-0.1'),
                fantasy=Decimal('0.6'),
                stats_nerd=Decimal('0.5')
            )

    def test_reject_score_above_one(self):
        """Test that score > 1 raises ValidationError."""
        with pytest.raises(ValidationError):
            PersonaScore(
                bettor=Decimal('0.2'),
                fantasy=Decimal('1.5'),
                stats_nerd=Decimal('0.3')
            )

    def test_primary_persona_bettor(self):
        """Test primary_persona when bettor is highest."""
        score = PersonaScore(
            bettor=Decimal('0.60'),
            fantasy=Decimal('0.25'),
            stats_nerd=Decimal('0.15')
        )
        assert score.primary_persona == "bettor"

    def test_primary_persona_fantasy(self):
        """Test primary_persona when fantasy is highest."""
        score = PersonaScore(
            bettor=Decimal('0.20'),
            fantasy=Decimal('0.55'),
            stats_nerd=Decimal('0.25')
        )
        assert score.primary_persona == "fantasy"

    def test_primary_persona_stats_nerd(self):
        """Test primary_persona when stats_nerd is highest."""
        score = PersonaScore(
            bettor=Decimal('0.15'),
            fantasy=Decimal('0.25'),
            stats_nerd=Decimal('0.60')
        )
        assert score.primary_persona == "stats_nerd"

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

    def test_confidence_property(self):
        """Test confidence returns max score."""
        score = PersonaScore(
            bettor=Decimal('0.80'),
            fantasy=Decimal('0.15'),
            stats_nerd=Decimal('0.05')
        )
        assert score.confidence == Decimal('0.80')

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

    def test_decimal_conversion(self):
        """Test that floats/strings are converted to Decimal."""
        score = PersonaScore(
            bettor=0.5,  # float
            fantasy="0.3",  # string
            stats_nerd=0.2  # float
        )
        assert isinstance(score.bettor, Decimal)
        assert isinstance(score.fantasy, Decimal)


# =============================================================================
# PatternWeights Tests
# =============================================================================

class TestPatternWeights:
    """Tests for PatternWeights model."""

    def test_create_default_weights(self):
        """Test creating PatternWeights with defaults."""
        weights = PatternWeights()
        assert weights.line_movement == Decimal('1.0')
        assert weights.historical_trends == Decimal('1.0')

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
        """Test that negative weight raises ValidationError."""
        with pytest.raises(ValidationError):
            PatternWeights(line_movement=Decimal('-0.5'))

    def test_apply_to_pattern(self):
        """Test apply_to_pattern method."""
        weights = PatternWeights(line_movement=Decimal('1.5'))
        base_score = Decimal('0.80')
        weighted = weights.apply_to_pattern(base_score, 'line_movement')
        assert weighted == Decimal('1.20')

    def test_decimal_conversion(self):
        """Test that floats/strings are converted to Decimal."""
        weights = PatternWeights(
            line_movement=1.5,  # float
            historical_trends="0.8",  # string
        )
        assert isinstance(weights.line_movement, Decimal)
        assert isinstance(weights.historical_trends, Decimal)

    def test_model_dump_serialization(self):
        """Test serialization to dictionary."""
        weights = PatternWeights(
            line_movement=Decimal('1.5'),
            situational_stats=Decimal('1.6')
        )
        data = weights.model_dump()

        assert data['line_movement'] == Decimal('1.5')
        assert data['situational_stats'] == Decimal('1.6')


# =============================================================================
# UserProfile Tests
# =============================================================================

class TestUserProfile:
    """Tests for UserProfile model."""

    @pytest.fixture
    def sample_metrics(self):
        """Create sample BehavioralMetrics."""
        return BehavioralMetrics(
            total_entries=100,
            entries_by_sport={"NFL": 100},
            entries_by_contest_type={"GPP": 100},
            total_invested=Decimal('500.00'),
            total_winnings=Decimal('600.00'),
            avg_entry_fee=Decimal('5.00'),
            roi_overall=Decimal('20.00'),
            gpp_percentage=Decimal('1.0'),
            cash_percentage=Decimal('0'),
            multi_entry_rate=Decimal('1.0'),
            sport_diversity=Decimal('0'),
            stake_variance=Decimal('0.1'),
            entries_per_week=Decimal('10'),
            most_active_day="Sunday",
            recency_score=Decimal('0.9'),
        )

    @pytest.fixture
    def sample_persona(self):
        """Create sample PersonaScore."""
        return PersonaScore(
            bettor=Decimal('0.6'),
            fantasy=Decimal('0.3'),
            stats_nerd=Decimal('0.1')
        )

    @pytest.fixture
    def sample_weights(self):
        """Create sample PatternWeights."""
        return PatternWeights(line_movement=Decimal('1.5'))

    def test_create_valid_profile(self, sample_metrics, sample_persona, sample_weights):
        """Test creating a valid UserProfile."""
        now = datetime.utcnow()
        profile = UserProfile(
            total_entries_parsed=100,
            date_range_start=datetime(2024, 1, 1),
            date_range_end=datetime(2024, 12, 31),
            platforms=["DK", "FD"],
            behavioral_metrics=sample_metrics,
            persona_scores=sample_persona,
            pattern_weights=sample_weights,
            last_csv_upload=now,
            confidence_score=Decimal('0.85')
        )

        assert profile.total_entries_parsed == 100
        assert isinstance(profile.user_id, UUID)
        assert profile.platforms == ["DK", "FD"]
        assert profile.persona_scores.primary_persona == "bettor"

    def test_uuid_auto_generated(self, sample_metrics, sample_persona, sample_weights):
        """Test that user_id is auto-generated."""
        profile = UserProfile(
            total_entries_parsed=10,
            date_range_start=datetime(2024, 1, 1),
            date_range_end=datetime(2024, 12, 31),
            platforms=["DK"],
            behavioral_metrics=sample_metrics,
            persona_scores=sample_persona,
            pattern_weights=sample_weights,
            last_csv_upload=datetime.utcnow(),
            confidence_score=Decimal('0.5')
        )
        assert isinstance(profile.user_id, UUID)

    def test_timestamps_auto_generated(self, sample_metrics, sample_persona, sample_weights):
        """Test that timestamps are auto-generated."""
        profile = UserProfile(
            total_entries_parsed=10,
            date_range_start=datetime(2024, 1, 1),
            date_range_end=datetime(2024, 12, 31),
            platforms=["DK"],
            behavioral_metrics=sample_metrics,
            persona_scores=sample_persona,
            pattern_weights=sample_weights,
            last_csv_upload=datetime.utcnow(),
            confidence_score=Decimal('0.5')
        )
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_nested_models_validate(self, sample_metrics, sample_persona, sample_weights):
        """Test that nested models are validated."""
        profile = UserProfile(
            total_entries_parsed=100,
            date_range_start=datetime(2024, 1, 1),
            date_range_end=datetime(2024, 12, 31),
            platforms=["DK"],
            behavioral_metrics=sample_metrics,
            persona_scores=sample_persona,
            pattern_weights=sample_weights,
            last_csv_upload=datetime.utcnow(),
            confidence_score=Decimal('0.85')
        )

        assert isinstance(profile.behavioral_metrics, BehavioralMetrics)
        assert isinstance(profile.persona_scores, PersonaScore)
        assert isinstance(profile.pattern_weights, PatternWeights)

    def test_model_dump_json_clean(self, sample_metrics, sample_persona, sample_weights):
        """Test that model serializes to JSON cleanly."""
        profile = UserProfile(
            total_entries_parsed=100,
            date_range_start=datetime(2024, 1, 1),
            date_range_end=datetime(2024, 12, 31),
            platforms=["DK"],
            behavioral_metrics=sample_metrics,
            persona_scores=sample_persona,
            pattern_weights=sample_weights,
            last_csv_upload=datetime.utcnow(),
            confidence_score=Decimal('0.85')
        )

        # Should not raise
        json_data = profile.model_dump_json()
        assert isinstance(json_data, str)
        assert "bettor" in json_data

    def test_reject_invalid_confidence_score(self, sample_metrics, sample_persona, sample_weights):
        """Test that confidence_score outside 0-1 raises ValidationError."""
        with pytest.raises(ValidationError):
            UserProfile(
                total_entries_parsed=100,
                date_range_start=datetime(2024, 1, 1),
                date_range_end=datetime(2024, 12, 31),
                platforms=["DK"],
                behavioral_metrics=sample_metrics,
                persona_scores=sample_persona,
                pattern_weights=sample_weights,
                last_csv_upload=datetime.utcnow(),
                confidence_score=Decimal('1.5')  # Invalid
            )
