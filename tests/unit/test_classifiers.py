"""
Unit tests for contest type classifiers.

Tests cover:
- GPP classification
- Cash game classification
- Head-to-head classification
- Multi-entry classification
- Unknown fallback
- Batch classification
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.classifiers.contest_type_classifier import (
    ContestTypeClassifier,
    classify_contest,
)
from src.models.dfs_entry import DFSEntry


class TestContestTypeClassifier:
    """Tests for contest type classification."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ContestTypeClassifier()

    # =========================================================================
    # GPP Classification
    # =========================================================================

    def test_classify_gpp_explicit(self, classifier):
        """Test explicit GPP keyword."""
        assert classifier.classify("NFL $20K GPP") == "GPP"

    def test_classify_gpp_tournament(self, classifier):
        """Test tournament keyword."""
        assert classifier.classify("NFL Tournament") == "GPP"

    def test_classify_gpp_prize_pool(self, classifier):
        """Test prize pool format ($XXK)."""
        assert classifier.classify("NFL $100K Sharpshooter") == "GPP"

    def test_classify_gpp_guaranteed(self, classifier):
        """Test guaranteed keyword."""
        assert classifier.classify("NFL Guaranteed $50K") == "GPP"

    def test_classify_gpp_gtd(self, classifier):
        """Test GTD abbreviation."""
        assert classifier.classify("NFL $500K GTD") == "GPP"

    def test_classify_gpp_million(self, classifier):
        """Test million keyword."""
        assert classifier.classify("NFL Sunday Million") == "GPP"

    def test_classify_gpp_showdown(self, classifier):
        """Test showdown keyword."""
        assert classifier.classify("NFL Showdown Captain") == "GPP"

    def test_classify_gpp_freeroll(self, classifier):
        """Test freeroll keyword."""
        assert classifier.classify("NFL Freeroll") == "GPP"

    # =========================================================================
    # Cash Game Classification
    # =========================================================================

    def test_classify_cash_50_50(self, classifier):
        """Test 50/50 format."""
        assert classifier.classify("NFL 50/50") == "CASH"

    def test_classify_cash_double_up(self, classifier):
        """Test double-up format."""
        assert classifier.classify("NBA Double Up") == "CASH"

    def test_classify_cash_double_dash_up(self, classifier):
        """Test double-up with hyphen."""
        assert classifier.classify("NBA Double-Up") == "CASH"

    def test_classify_cash_game(self, classifier):
        """Test cash game keyword."""
        assert classifier.classify("NFL Cash Game") == "CASH"

    # =========================================================================
    # Head-to-Head Classification
    # =========================================================================

    def test_classify_h2h_explicit(self, classifier):
        """Test explicit H2H."""
        assert classifier.classify("NFL H2H $5") == "H2H"

    def test_classify_h2h_head_to_head(self, classifier):
        """Test head to head format."""
        assert classifier.classify("NFL Head to Head") == "H2H"

    def test_classify_h2h_heads_up(self, classifier):
        """Test heads up format."""
        assert classifier.classify("NBA Heads Up") == "H2H"

    def test_classify_h2h_1v1(self, classifier):
        """Test 1v1 format."""
        assert classifier.classify("NHL 1v1") == "H2H"

    # =========================================================================
    # Multi-Entry Classification
    # =========================================================================

    def test_classify_multi_max(self, classifier):
        """Test X-max format."""
        assert classifier.classify("NFL 3-Max GPP") == "MULTI"

    def test_classify_multi_entry(self, classifier):
        """Test multi-entry format."""
        assert classifier.classify("NBA Multi-Entry") == "MULTI"

    def test_classify_multi_150_entry(self, classifier):
        """Test 150-entry format."""
        assert classifier.classify("NFL 150-Entry Tournament") == "MULTI"

    # =========================================================================
    # Priority Order Tests
    # =========================================================================

    def test_priority_h2h_over_cash(self, classifier):
        """Test H2H has priority over cash keywords."""
        # If a contest has both, H2H should win
        assert classifier.classify("H2H Double Up") == "H2H"

    def test_priority_cash_over_gpp(self, classifier):
        """Test CASH has priority over GPP keywords."""
        # 50/50 should be CASH even with tournament money
        assert classifier.classify("50/50 $20K") == "CASH"

    def test_priority_multi_over_gpp(self, classifier):
        """Test MULTI has priority over GPP keywords."""
        assert classifier.classify("3-Max $100K Tournament") == "MULTI"

    # =========================================================================
    # Unknown Classification
    # =========================================================================

    def test_classify_unknown(self, classifier):
        """Test unknown contest type."""
        assert classifier.classify("Mystery Contest") == "UNKNOWN"

    def test_classify_empty(self, classifier):
        """Test empty string."""
        assert classifier.classify("") == "UNKNOWN"

    def test_classify_none_like(self, classifier):
        """Test None-like value."""
        assert classifier.classify("None") == "UNKNOWN"

    # =========================================================================
    # Entry Classification
    # =========================================================================

    def test_classify_entry(self, classifier):
        """Test classifying a DFSEntry."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="UNKNOWN",
            entry_fee=Decimal('5.00'),
            winnings=Decimal('0'),
            points=Decimal('100'),
            source="DRAFTKINGS",
            contest_name="NFL $20K Sharpshooter",
        )

        classified = classifier.classify_entry(entry)

        assert classified.contest_type == "GPP"
        assert classified.entry_id == entry.entry_id
        assert classified.entry_fee == entry.entry_fee

    def test_classify_entries_batch(self, classifier):
        """Test batch classification."""
        entries = [
            DFSEntry(
                entry_id="1",
                date=datetime.now(),
                sport="NFL",
                contest_type="UNKNOWN",
                entry_fee=Decimal('5.00'),
                winnings=Decimal('0'),
                points=Decimal('100'),
                source="DRAFTKINGS",
                contest_name="NFL $20K GPP",
            ),
            DFSEntry(
                entry_id="2",
                date=datetime.now(),
                sport="NBA",
                contest_type="UNKNOWN",
                entry_fee=Decimal('3.00'),
                winnings=Decimal('5.40'),
                points=Decimal('200'),
                source="DRAFTKINGS",
                contest_name="NBA 50/50",
            ),
        ]

        classified = classifier.classify_entries(entries)

        assert len(classified) == 2
        assert classified[0].contest_type == "GPP"
        assert classified[1].contest_type == "CASH"

    # =========================================================================
    # Module Function Tests
    # =========================================================================

    def test_classify_contest_function(self):
        """Test module-level classify_contest function."""
        assert classify_contest("NFL $20K GPP") == "GPP"
        assert classify_contest("NBA 50/50") == "CASH"

    # =========================================================================
    # Case Insensitivity Tests
    # =========================================================================

    def test_case_insensitive_gpp(self, classifier):
        """Test GPP is case insensitive."""
        assert classifier.classify("nfl gpp") == "GPP"
        assert classifier.classify("NFL GPP") == "GPP"

    def test_case_insensitive_h2h(self, classifier):
        """Test H2H is case insensitive."""
        assert classifier.classify("nfl h2h") == "H2H"
        assert classifier.classify("NFL H2H") == "H2H"

    # =========================================================================
    # Debug Method Tests
    # =========================================================================

    def test_get_pattern_match_found(self, classifier):
        """Test get_pattern_match returns matching pattern."""
        pattern = classifier.get_pattern_match("NFL $20K GPP")
        assert pattern is not None
        assert "GPP" in pattern or "$" in pattern

    def test_get_pattern_match_not_found(self, classifier):
        """Test get_pattern_match returns None for no match."""
        pattern = classifier.get_pattern_match("Mystery Contest")
        assert pattern is None
