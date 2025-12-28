"""
Integration tests for the parsing pipeline.

Tests the complete flow: CSV file -> platform detection -> parsing -> classification
"""

import pytest
from pathlib import Path
from decimal import Decimal

from src.parsers.platform_detector import detect_platform
from src.parsers.draftkings_parser import DraftKingsParser
from src.parsers.fanduel_parser import FanDuelParser
from src.classifiers.contest_type_classifier import ContestTypeClassifier


class TestParsingPipeline:
    """Integration tests for CSV parsing pipeline."""

    @pytest.fixture
    def fixtures_path(self):
        """Get path to test fixtures."""
        return Path(__file__).parent.parent / "fixtures"

    def test_draftkings_full_pipeline(self, fixtures_path):
        """Test complete DraftKings parsing pipeline."""
        csv_path = fixtures_path / "sample_draftkings.csv"

        # Step 1: Detect platform
        platform = detect_platform(csv_path)
        assert platform == "DRAFTKINGS"

        # Step 2: Parse CSV
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)
        assert len(entries) == 8

        # Step 3: Classify contests
        classifier = ContestTypeClassifier()
        classified = classifier.classify_entries(entries)

        # Verify all entries are classified
        assert len(classified) == 8
        assert all(e.contest_type != "" for e in classified)

        # Verify specific classifications
        contest_types = {e.contest_name: e.contest_type for e in classified}
        assert "NFL $20K Sharpshooter" in contest_types or any("GPP" in ct for ct in contest_types.values())

    def test_fanduel_full_pipeline(self, fixtures_path):
        """Test complete FanDuel parsing pipeline."""
        csv_path = fixtures_path / "sample_fanduel.csv"

        # Step 1: Detect platform
        platform = detect_platform(csv_path)
        assert platform == "FANDUEL"

        # Step 2: Parse CSV
        parser = FanDuelParser()
        entries = parser.parse(csv_path)
        assert len(entries) == 6

        # Step 3: Classify contests
        classifier = ContestTypeClassifier()
        classified = classifier.classify_entries(entries)

        # Verify classifications
        types_found = set(e.contest_type for e in classified)
        assert "GPP" in types_found or "CASH" in types_found or "H2H" in types_found

    def test_auto_parser_selection(self, fixtures_path):
        """Test automatic parser selection based on platform detection."""
        for csv_file, expected_platform, expected_source in [
            ("sample_draftkings.csv", "DRAFTKINGS", "DK"),
            ("sample_fanduel.csv", "FANDUEL", "FD"),
        ]:
            csv_path = fixtures_path / csv_file
            platform = detect_platform(csv_path)

            if platform == "DRAFTKINGS":
                parser = DraftKingsParser()
            else:
                parser = FanDuelParser()

            entries = parser.parse(csv_path)
            assert len(entries) > 0
            assert all(e.source == expected_source for e in entries)

    def test_currency_parsing_accuracy(self, fixtures_path):
        """Test that currency values are parsed correctly as Decimal."""
        csv_path = fixtures_path / "sample_draftkings.csv"
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)

        # Verify all entry fees are Decimal
        for entry in entries:
            assert isinstance(entry.entry_fee, Decimal)
            assert isinstance(entry.winnings, Decimal)
            assert entry.entry_fee >= Decimal('0')

    def test_date_parsing_accuracy(self, fixtures_path):
        """Test that dates are parsed correctly."""
        csv_path = fixtures_path / "sample_draftkings.csv"
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)

        # Verify dates are datetime objects
        from datetime import datetime
        for entry in entries:
            assert isinstance(entry.date, datetime)
            assert entry.date.year >= 2020  # Sanity check

    def test_sport_normalization(self, fixtures_path):
        """Test that sports are normalized to uppercase."""
        csv_path = fixtures_path / "sample_draftkings.csv"
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)

        # All sports should be uppercase
        for entry in entries:
            assert entry.sport == entry.sport.upper()

    def test_classification_distribution(self, fixtures_path):
        """Test contest type classification distribution."""
        csv_path = fixtures_path / "sample_draftkings.csv"
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)

        classifier = ContestTypeClassifier()
        classified = classifier.classify_entries(entries)

        # Count contest types
        type_counts = {}
        for entry in classified:
            type_counts[entry.contest_type] = type_counts.get(entry.contest_type, 0) + 1

        # Should have multiple types
        assert len(type_counts) >= 2, f"Expected multiple contest types, got: {type_counts}"

    def test_malformed_row_handling(self, fixtures_path):
        """Test handling of edge cases in CSV."""
        csv_path = fixtures_path / "sample_edge_cases.csv"
        parser = DraftKingsParser()

        # Should not raise, but may skip some rows
        entries = parser.parse(csv_path)

        # Check warnings were generated for problematic rows
        if parser.warnings:
            assert any("Skipping" in w for w in parser.warnings)
