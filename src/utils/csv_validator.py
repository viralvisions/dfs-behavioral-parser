"""
CSV Validator for DFS exports.

Validates file size, extension, and detects platform from headers.
"""

import csv
from typing import Literal
from io import StringIO

PlatformType = Literal["DRAFTKINGS", "FANDUEL", "UNKNOWN"]


class CSVValidator:
    """Validate and detect CSV platform"""

    DK_REQUIRED_COLUMNS = [
        "Entry ID", "Contest Name", "Entry Fee",
        "Winnings", "Sport", "Date Entered"
    ]

    FD_REQUIRED_COLUMNS = [
        "Entry Id", "Contest", "Entry Fee",
        "Winnings", "Sport", "Entered"
    ]

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def validate_size(self, content: str) -> None:
        """Ensure file is under size limit"""
        size = len(content.encode('utf-8'))
        if size > self.MAX_FILE_SIZE:
            raise ValueError(f"CSV file exceeds 10MB limit ({size / 1024 / 1024:.1f}MB)")

    def validate_extension(self, filename: str) -> bool:
        """Only accept .csv files"""
        return filename.lower().endswith('.csv')

    def detect_platform(self, csv_content: str) -> PlatformType:
        """Detect DraftKings vs FanDuel from headers"""
        reader = csv.DictReader(StringIO(csv_content))
        headers = reader.fieldnames or []

        dk_match = all(col in headers for col in self.DK_REQUIRED_COLUMNS)
        fd_match = all(col in headers for col in self.FD_REQUIRED_COLUMNS)

        if dk_match:
            return "DRAFTKINGS"
        elif fd_match:
            return "FANDUEL"
        else:
            return "UNKNOWN"

    def sanitize_field(self, value: str) -> str:
        """Remove potentially malicious characters from CSV field"""
        if not value:
            return value
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
        result = str(value)
        for char in dangerous_chars:
            result = result.replace(char, "")
        return result.strip()
