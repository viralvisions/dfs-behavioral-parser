"""
DFS History Parser - Unified parser for DraftKings/FanDuel CSVs.

Parses CSVs into normalized DFSEntry objects with auto-detection.
"""

import csv
from decimal import Decimal
from datetime import datetime
from typing import List
from io import StringIO

from .draftkings_parser import DraftKingsParser
from .fanduel_parser import FanDuelParser
from ..classifiers.contest_type_classifier import ContestTypeClassifier
from ..models.dfs_entry import DFSEntry
from ..utils.csv_validator import CSVValidator


class DFSHistoryParser:
    """
    Parse DraftKings/FanDuel CSVs into normalized DFSEntry objects.
    Why: Different platforms = different formats, need single pipeline.
    """

    def __init__(self):
        self.validator = CSVValidator()
        self.classifier = ContestTypeClassifier()
        self._dk_parser = DraftKingsParser()
        self._fd_parser = FanDuelParser()

    def parse_csv_string(self, csv_content: str) -> List[DFSEntry]:
        """Main entry point for CSV parsing"""
        # Validate size
        self.validator.validate_size(csv_content)

        # Detect platform
        platform = self.validator.detect_platform(csv_content)

        if platform == "DRAFTKINGS":
            entries = self._dk_parser.parse(StringIO(csv_content))
        elif platform == "FANDUEL":
            entries = self._fd_parser.parse(StringIO(csv_content))
        else:
            raise ValueError("Unknown CSV format - must be DraftKings or FanDuel")

        # Classify contest types for all entries
        return self.classifier.classify_entries(entries)

    def parse_file(self, file_path: str) -> List[DFSEntry]:
        """Parse a CSV file from disk"""
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        return self.parse_csv_string(content)
