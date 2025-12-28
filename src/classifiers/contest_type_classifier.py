"""
Contest type classifier using regex pattern matching.

Classifies DFS contests into types: GPP, CASH, H2H, MULTI, UNKNOWN
based on contest name patterns.
"""

import re
from typing import List, Optional

from src.models.dfs_entry import DFSEntry
from src.utils.constants import (
    CONTEST_GPP,
    CONTEST_CASH,
    CONTEST_H2H,
    CONTEST_MULTI,
    CONTEST_UNKNOWN,
    CONTEST_PATTERNS,
)


class ContestTypeClassifier:
    """
    Pattern-based classifier for DFS contest types.

    Uses regex patterns to classify contests. Priority order:
    1. H2H (head-to-head) - most specific
    2. CASH (50/50, double-ups)
    3. MULTI (multi-entry indicators)
    4. GPP (tournaments) - most common
    5. UNKNOWN (fallback)

    Example usage:
        classifier = ContestTypeClassifier()
        contest_type = classifier.classify("NFL $20K Sharpshooter")
        # Returns: "GPP"
    """

    # Classification priority order (most specific first)
    PRIORITY_ORDER = [CONTEST_H2H, CONTEST_CASH, CONTEST_MULTI, CONTEST_GPP]

    def __init__(self) -> None:
        """Initialize classifier with compiled regex patterns."""
        self._compiled_patterns = {}
        for contest_type, patterns in CONTEST_PATTERNS.items():
            self._compiled_patterns[contest_type] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in patterns
            ]

    def classify(self, contest_name: str) -> str:
        """
        Classify a single contest name into a contest type.

        Checks patterns in priority order - first match wins.

        Args:
            contest_name: The contest name string to classify

        Returns:
            Contest type: "GPP", "CASH", "H2H", "MULTI", or "UNKNOWN"

        Examples:
            >>> classifier = ContestTypeClassifier()
            >>> classifier.classify("NFL $20K Sharpshooter")
            'GPP'
            >>> classifier.classify("50/50 Double Up")
            'CASH'
            >>> classifier.classify("H2H $5")
            'H2H'
        """
        if not contest_name:
            return CONTEST_UNKNOWN

        contest_name = str(contest_name)

        # Check each contest type in priority order
        for contest_type in self.PRIORITY_ORDER:
            if self._matches_type(contest_name, contest_type):
                return contest_type

        return CONTEST_UNKNOWN

    def _matches_type(self, contest_name: str, contest_type: str) -> bool:
        """
        Check if contest name matches any pattern for the given type.

        Args:
            contest_name: Contest name to check
            contest_type: Type to check patterns for

        Returns:
            True if any pattern matches
        """
        patterns = self._compiled_patterns.get(contest_type, [])
        for pattern in patterns:
            if pattern.search(contest_name):
                return True
        return False

    def classify_entry(self, entry: DFSEntry) -> DFSEntry:
        """
        Classify an entry and return a new entry with contest_type set.

        Args:
            entry: DFSEntry with contest_name

        Returns:
            New DFSEntry with contest_type populated
        """
        contest_type = self.classify(entry.contest_name or "")

        return DFSEntry(
            entry_id=entry.entry_id,
            date=entry.date,
            sport=entry.sport,
            contest_type=contest_type,
            entry_fee=entry.entry_fee,
            winnings=entry.winnings,
            points=entry.points,
            source=entry.source,
            contest_name=entry.contest_name,
        )

    def classify_entries(self, entries: List[DFSEntry]) -> List[DFSEntry]:
        """
        Classify a list of entries.

        Args:
            entries: List of DFSEntry objects

        Returns:
            New list with contest_type populated for each entry
        """
        return [self.classify_entry(entry) for entry in entries]

    def get_pattern_match(self, contest_name: str) -> Optional[str]:
        """
        Get the specific pattern that matched for debugging.

        Args:
            contest_name: Contest name to check

        Returns:
            The pattern string that matched, or None
        """
        for contest_type in self.PRIORITY_ORDER:
            for pattern in self._compiled_patterns.get(contest_type, []):
                if pattern.search(contest_name):
                    return pattern.pattern
        return None


# Module-level convenience function
_default_classifier = None


def classify_contest(contest_name: str) -> str:
    """
    Classify a contest name using the default classifier.

    Convenience function for one-off classification without
    instantiating a classifier.

    Args:
        contest_name: The contest name to classify

    Returns:
        Contest type string
    """
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = ContestTypeClassifier()
    return _default_classifier.classify(contest_name)
