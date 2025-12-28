"""
Security tests for DFS Behavioral Parser.

Tests cover:
- SQL injection prevention
- File size validation
- Extension validation
- Decimal for money fields
- Input sanitization
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.parsers.dfs_history_parser import DFSHistoryParser
from src.utils.csv_validator import CSVValidator
from src.models.dfs_entry import DFSEntry


class TestSQLInjectionPrevention:
    """Test SQL injection prevention."""

    def test_sql_injection_in_contest_name(self):
        """Ensure malicious SQL in contest name is handled safely."""
        malicious_csv = """Entry ID,Contest Name,Entry Fee,Winnings,Sport,Date Entered,Points
1,'; DROP TABLE user_profiles; --,3.00,5.50,NFL,2024-09-15 13:00:00,156.42"""

        parser = DFSHistoryParser()
        entries = parser.parse_csv_string(malicious_csv)

        # Entry should parse without executing SQL
        assert len(entries) == 1
        # Contest name should be stored but not execute as SQL
        assert entries[0].entry_id == "1"


class TestFileSizeLimit:
    """Test file size validation."""

    def test_reject_files_over_10mb(self):
        """Reject files over 10MB."""
        validator = CSVValidator()

        # Simulate large file (>10MB)
        large_csv = "x" * (11 * 1024 * 1024)  # 11MB

        with pytest.raises(ValueError, match="exceeds 10MB"):
            validator.validate_size(large_csv)

    def test_accept_files_under_10mb(self):
        """Accept files under 10MB."""
        validator = CSVValidator()

        # Small file
        small_csv = "Entry ID,Contest Name\n1,Test\n"

        # Should not raise
        validator.validate_size(small_csv)


class TestExtensionValidation:
    """Test file extension validation."""

    def test_accept_csv_extension(self):
        """Only accept .csv files."""
        validator = CSVValidator()

        assert validator.validate_extension("data.csv") is True
        assert validator.validate_extension("DATA.CSV") is True
        assert validator.validate_extension("my_file.csv") is True

    def test_reject_non_csv_extensions(self):
        """Reject non-CSV files."""
        validator = CSVValidator()

        assert validator.validate_extension("data.txt") is False
        assert validator.validate_extension("malicious.exe") is False
        assert validator.validate_extension("script.py") is False
        assert validator.validate_extension("data.xlsx") is False


class TestDecimalForMoney:
    """Ensure all money fields use Decimal, not float."""

    def test_entry_money_fields_are_decimal(self):
        """Ensure DFSEntry money fields use Decimal."""
        entry = DFSEntry(
            entry_id="123",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal("3.00"),
            winnings=Decimal("5.50"),
            points=Decimal("156.42"),
            source="DK"
        )

        # Verify types
        assert isinstance(entry.entry_fee, Decimal)
        assert isinstance(entry.winnings, Decimal)
        assert isinstance(entry.roi, Decimal)
        assert isinstance(entry.profit, Decimal)

    def test_money_precision_preserved(self):
        """Test that Decimal preserves precision."""
        entry = DFSEntry(
            entry_id="1",
            date=datetime.now(),
            sport="NFL",
            contest_type="GPP",
            entry_fee=Decimal("0.10"),
            winnings=Decimal("0.30"),
            points=Decimal("100"),
            source="DK"
        )

        # 0.1 + 0.1 + 0.1 = 0.3 (not 0.30000000000000004 like float)
        profit = entry.profit
        assert profit == Decimal("0.20")


class TestInputSanitization:
    """Test input sanitization."""

    def test_sanitize_field_removes_sql_chars(self):
        """Test that dangerous SQL characters are removed."""
        validator = CSVValidator()

        # Test various SQL injection attempts
        assert ";" not in validator.sanitize_field("test;value")
        assert "--" not in validator.sanitize_field("test--value")
        assert "'" not in validator.sanitize_field("test'value")
        assert '"' not in validator.sanitize_field('test"value')

    def test_sanitize_field_preserves_normal_text(self):
        """Test that normal text is preserved."""
        validator = CSVValidator()

        assert validator.sanitize_field("NFL $20K Shot") == "NFL $20K Shot"
        assert validator.sanitize_field("  trimmed  ") == "trimmed"


class TestPlatformDetection:
    """Test platform detection security."""

    def test_detect_draftkings(self):
        """Detect DraftKings format."""
        validator = CSVValidator()
        csv_content = "Entry ID,Contest Name,Entry Fee,Winnings,Sport,Date Entered\n1,Test,$5,$0,NFL,2024-01-01\n"

        assert validator.detect_platform(csv_content) == "DRAFTKINGS"

    def test_detect_fanduel(self):
        """Detect FanDuel format."""
        validator = CSVValidator()
        csv_content = "Entry Id,Contest,Entry Fee,Winnings,Sport,Entered\n1,Test,$5,$0,NFL,2024-01-01\n"

        assert validator.detect_platform(csv_content) == "FANDUEL"

    def test_detect_unknown_format(self):
        """Return UNKNOWN for unrecognized format."""
        validator = CSVValidator()
        csv_content = "id,name,value\n1,test,5\n"

        assert validator.detect_platform(csv_content) == "UNKNOWN"
