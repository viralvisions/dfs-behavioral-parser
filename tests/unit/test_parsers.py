"""
Unit tests for CSV parsers and utilities.

Tests cover:
- Date parsing
- Platform detection
- DraftKings parsing
- FanDuel parsing
- Currency cleaning
"""

import pytest
from datetime import datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path

from src.utils.date_parser import parse_date, parse_date_safe
from src.parsers.platform_detector import (
    detect_platform,
    detect_platform_from_headers,
    is_draftkings,
    is_fanduel,
)
from src.parsers.draftkings_parser import DraftKingsParser
from src.parsers.fanduel_parser import FanDuelParser
from src.parsers.base_parser import BaseParser


# =============================================================================
# Date Parser Tests
# =============================================================================

class TestDateParser:
    """Tests for date parsing utility."""

    def test_parse_iso_format(self):
        """Test parsing ISO format date."""
        result = parse_date("2024-09-15 13:00:00")
        assert result == datetime(2024, 9, 15, 13, 0, 0)

    def test_parse_date_only(self):
        """Test parsing date without time."""
        result = parse_date("2024-09-15")
        assert result == datetime(2024, 9, 15, 0, 0, 0)

    def test_parse_us_format(self):
        """Test parsing US date format."""
        result = parse_date("09/15/2024")
        assert result == datetime(2024, 9, 15, 0, 0, 0)

    def test_parse_fanduel_format(self):
        """Test parsing FanDuel date format."""
        result = parse_date("Sep 15, 2024 1:00PM")
        assert result == datetime(2024, 9, 15, 13, 0, 0)

    def test_parse_fanduel_format_with_space(self):
        """Test parsing FanDuel format with space before AM/PM."""
        result = parse_date("Sep 15, 2024 1:00 PM")
        assert result == datetime(2024, 9, 15, 13, 0, 0)

    def test_parse_invalid_raises(self):
        """Test that invalid date raises ValueError."""
        with pytest.raises(ValueError, match="Could not parse date"):
            parse_date("not a date")

    def test_parse_empty_raises(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_date("")

    def test_parse_date_safe_returns_default(self):
        """Test parse_date_safe returns default on failure."""
        default = datetime(2024, 1, 1)
        result = parse_date_safe("invalid", default)
        assert result == default

    def test_parse_date_safe_success(self):
        """Test parse_date_safe succeeds on valid date."""
        result = parse_date_safe("2024-09-15")
        assert result == datetime(2024, 9, 15, 0, 0, 0)


# =============================================================================
# Platform Detector Tests
# =============================================================================

class TestPlatformDetector:
    """Tests for platform detection."""

    def test_detect_draftkings_from_string(self):
        """Test detecting DraftKings from CSV string."""
        csv_data = StringIO(
            "Entry ID,Contest Name,Entry Fee,Winnings,Points,Sport,Date Entered\n"
            "1,Test,$5.00,$0.00,100,NFL,2024-09-15\n"
        )
        assert detect_platform(csv_data) == "DRAFTKINGS"

    def test_detect_fanduel_from_string(self):
        """Test detecting FanDuel from CSV string."""
        csv_data = StringIO(
            "Entry Id,Contest,Entry Fee,Winnings,Points,Sport,Entered\n"
            "1,Test,$5.00,$0.00,100,NFL,2024-09-15\n"
        )
        assert detect_platform(csv_data) == "FANDUEL"

    def test_detect_draftkings_from_headers(self):
        """Test detecting DraftKings from header list."""
        headers = ["Entry ID", "Contest Name", "Entry Fee", "Winnings", "Sport", "Date Entered"]
        assert detect_platform_from_headers(headers) == "DRAFTKINGS"

    def test_detect_fanduel_from_headers(self):
        """Test detecting FanDuel from header list."""
        headers = ["Entry Id", "Contest", "Entry Fee", "Winnings", "Sport", "Entered"]
        assert detect_platform_from_headers(headers) == "FANDUEL"

    def test_unknown_platform_raises(self):
        """Test that unknown format raises ValueError."""
        csv_data = StringIO(
            "id,name,fee\n"
            "1,Test,5.00\n"
        )
        with pytest.raises(ValueError, match="Could not detect platform"):
            detect_platform(csv_data)

    def test_is_draftkings_true(self):
        """Test is_draftkings returns True for DK format."""
        csv_data = StringIO(
            "Entry ID,Contest Name,Entry Fee,Winnings,Points,Sport,Date Entered\n"
        )
        assert is_draftkings(csv_data) is True

    def test_is_draftkings_false(self):
        """Test is_draftkings returns False for FD format."""
        csv_data = StringIO(
            "Entry Id,Contest,Entry Fee,Winnings,Points,Sport,Entered\n"
        )
        assert is_draftkings(csv_data) is False

    def test_is_fanduel_true(self):
        """Test is_fanduel returns True for FD format."""
        csv_data = StringIO(
            "Entry Id,Contest,Entry Fee,Winnings,Points,Sport,Entered\n"
        )
        assert is_fanduel(csv_data) is True


# =============================================================================
# DraftKings Parser Tests
# =============================================================================

class TestDraftKingsParser:
    """Tests for DraftKings CSV parser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return DraftKingsParser()

    @pytest.fixture
    def sample_csv(self):
        """Create sample DraftKings CSV."""
        return StringIO(
            "Entry ID,Contest Name,Entry Fee,Winnings,Points,Sport,Date Entered\n"
            "DK001,NFL $20K Shot,$5.00,$10.00,150.5,NFL,2024-09-15 13:00:00\n"
            "DK002,NBA 50/50,$3.00,$5.40,200.0,NBA,2024-10-01 19:00:00\n"
        )

    def test_parse_basic(self, parser, sample_csv):
        """Test basic parsing."""
        entries = parser.parse(sample_csv)
        assert len(entries) == 2

    def test_parse_entry_fields(self, parser, sample_csv):
        """Test parsed entry fields."""
        entries = parser.parse(sample_csv)
        entry = entries[0]

        assert entry.entry_id == "DK001"
        assert entry.source == "DRAFTKINGS"
        assert entry.sport == "NFL"
        assert entry.entry_fee == Decimal('5.00')
        assert entry.winnings == Decimal('10.00')
        assert entry.points == Decimal('150.5')

    def test_parse_date(self, parser, sample_csv):
        """Test date parsing."""
        entries = parser.parse(sample_csv)
        assert entries[0].date == datetime(2024, 9, 15, 13, 0, 0)

    def test_parse_currency_with_symbols(self, parser):
        """Test parsing currency with $ symbols."""
        csv_data = StringIO(
            "Entry ID,Contest Name,Entry Fee,Winnings,Points,Sport,Date Entered\n"
            "1,Test,$5.00,$10.50,100,NFL,2024-09-15\n"
        )
        entries = parser.parse(csv_data)
        assert entries[0].entry_fee == Decimal('5.00')
        assert entries[0].winnings == Decimal('10.50')

    def test_parse_currency_with_commas(self, parser):
        """Test parsing currency with comma separators."""
        csv_data = StringIO(
            "Entry ID,Contest Name,Entry Fee,Winnings,Points,Sport,Date Entered\n"
            '1,Test,"$1,234.56","$5,000.00",100,NFL,2024-09-15\n'
        )
        entries = parser.parse(csv_data)
        assert entries[0].entry_fee == Decimal('1234.56')
        assert entries[0].winnings == Decimal('5000.00')

    def test_parse_missing_points(self, parser):
        """Test parsing with missing points."""
        csv_data = StringIO(
            "Entry ID,Contest Name,Entry Fee,Winnings,Points,Sport,Date Entered\n"
            "1,Test,$5.00,$0.00,,NFL,2024-09-15\n"
        )
        entries = parser.parse(csv_data)
        assert entries[0].points == Decimal('0')

    def test_parse_sample_file(self, parser):
        """Test parsing sample fixture file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_draftkings.csv"
        entries = parser.parse(fixture_path)

        assert len(entries) == 8
        assert all(e.source == "DRAFTKINGS" for e in entries)

    def test_missing_columns_raises(self, parser):
        """Test that missing required columns raises."""
        csv_data = StringIO(
            "Entry ID,Contest Name\n"
            "1,Test\n"
        )
        with pytest.raises(ValueError, match="Missing required columns"):
            parser.parse(csv_data)


# =============================================================================
# FanDuel Parser Tests
# =============================================================================

class TestFanDuelParser:
    """Tests for FanDuel CSV parser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return FanDuelParser()

    @pytest.fixture
    def sample_csv(self):
        """Create sample FanDuel CSV."""
        return StringIO(
            'Entry Id,Contest,Entry Fee,Winnings,Points,Sport,Entered\n'
            'FD001,NFL Sunday Million,$25.00,$50.00,185.4,NFL,"Sep 15, 2024 1:00PM"\n'
            'FD002,NBA 50/50,$5.00,$9.00,278.3,NBA,"Oct 20, 2024 7:00PM"\n'
        )

    def test_parse_basic(self, parser, sample_csv):
        """Test basic parsing."""
        entries = parser.parse(sample_csv)
        assert len(entries) == 2

    def test_parse_entry_fields(self, parser, sample_csv):
        """Test parsed entry fields."""
        entries = parser.parse(sample_csv)
        entry = entries[0]

        assert entry.entry_id == "FD001"
        assert entry.source == "FANDUEL"
        assert entry.sport == "NFL"
        assert entry.entry_fee == Decimal('25.00')
        assert entry.winnings == Decimal('50.00')

    def test_parse_fanduel_date(self, parser, sample_csv):
        """Test FanDuel date format parsing."""
        entries = parser.parse(sample_csv)
        assert entries[0].date == datetime(2024, 9, 15, 13, 0, 0)

    def test_parse_sample_file(self, parser):
        """Test parsing sample fixture file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_fanduel.csv"
        entries = parser.parse(fixture_path)

        assert len(entries) == 6
        assert all(e.source == "FANDUEL" for e in entries)


# =============================================================================
# Base Parser Currency Cleaning Tests
# =============================================================================

class TestCurrencyCleaning:
    """Tests for currency cleaning in base parser."""

    def test_clean_currency_with_dollar_sign(self):
        """Test cleaning $5.00 format."""
        result = BaseParser._clean_currency("$5.00")
        assert result == Decimal('5.00')

    def test_clean_currency_without_symbol(self):
        """Test cleaning plain number."""
        result = BaseParser._clean_currency("5.00")
        assert result == Decimal('5.00')

    def test_clean_currency_numeric(self):
        """Test cleaning numeric value."""
        result = BaseParser._clean_currency(5.00)
        assert result == Decimal('5')

    def test_clean_currency_with_commas(self):
        """Test cleaning $1,234.56 format."""
        result = BaseParser._clean_currency("$1,234.56")
        assert result == Decimal('1234.56')

    def test_clean_currency_dash(self):
        """Test cleaning dash (meaning zero)."""
        result = BaseParser._clean_currency("-")
        assert result == Decimal('0')

    def test_clean_currency_empty(self):
        """Test cleaning empty string."""
        result = BaseParser._clean_currency("")
        assert result == Decimal('0')

    def test_clean_currency_invalid_raises(self):
        """Test that invalid value raises."""
        with pytest.raises(ValueError, match="Cannot convert"):
            BaseParser._clean_currency("not money")
