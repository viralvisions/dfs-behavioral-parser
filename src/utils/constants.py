"""
Constants for DFS Behavioral Parser.

This module contains all magic numbers, string identifiers, and configuration
values used throughout the application. Centralizing these makes the codebase
easier to maintain and tune.
"""

from decimal import Decimal
from typing import Dict, Tuple, Set


# =============================================================================
# PLATFORM IDENTIFIERS
# =============================================================================

# Full platform names (for detection)
PLATFORM_DRAFTKINGS = "DRAFTKINGS"
PLATFORM_FANDUEL = "FANDUEL"

# Short platform codes (for DFSEntry.source)
PLATFORM_DK = "DK"
PLATFORM_FD = "FD"

VALID_PLATFORMS: Set[str] = {PLATFORM_DRAFTKINGS, PLATFORM_FANDUEL}
VALID_SOURCES: Set[str] = {PLATFORM_DK, PLATFORM_FD}


# =============================================================================
# CONTEST TYPES
# =============================================================================

CONTEST_GPP = "GPP"          # Guaranteed Prize Pool (tournaments)
CONTEST_CASH = "CASH"        # Cash games (50/50, double-ups)
CONTEST_H2H = "H2H"          # Head-to-head
CONTEST_MULTI = "MULTI"      # Multi-entry (same user, multiple lineups)
CONTEST_UNKNOWN = "UNKNOWN"  # Could not classify

VALID_CONTEST_TYPES: Set[str] = {
    CONTEST_GPP,
    CONTEST_CASH,
    CONTEST_H2H,
    CONTEST_MULTI,
    CONTEST_UNKNOWN,
}


# =============================================================================
# SPORT MAPPINGS
# =============================================================================

# Standard sport codes (uppercase)
SPORTS: Set[str] = {
    "NFL",    # Football
    "NBA",    # Basketball
    "MLB",    # Baseball
    "NHL",    # Hockey
    "PGA",    # Golf
    "NASCAR", # Auto racing
    "MMA",    # Mixed martial arts
    "SOCCER", # Soccer/Football
    "TENNIS", # Tennis
    "CBB",    # College basketball
    "CFB",    # College football
}

# Aliases map to canonical sport codes
SPORT_ALIASES: Dict[str, str] = {
    "FOOTBALL": "NFL",
    "BASKETBALL": "NBA",
    "BASEBALL": "MLB",
    "HOCKEY": "NHL",
    "GOLF": "PGA",
    "UFC": "MMA",
    "NCAAB": "CBB",
    "NCAAF": "CFB",
    "COLLEGE BASKETBALL": "CBB",
    "COLLEGE FOOTBALL": "CFB",
}


# =============================================================================
# DRAFTKINGS CSV COLUMNS
# =============================================================================

DK_COLUMN_ENTRY_ID = "Entry ID"
DK_COLUMN_CONTEST_NAME = "Contest Name"
DK_COLUMN_ENTRY_FEE = "Entry Fee"
DK_COLUMN_WINNINGS = "Winnings"
DK_COLUMN_POINTS = "Points"
DK_COLUMN_SPORT = "Sport"
DK_COLUMN_DATE = "Date Entered"

DK_REQUIRED_COLUMNS: Set[str] = {
    DK_COLUMN_ENTRY_ID,
    DK_COLUMN_CONTEST_NAME,
    DK_COLUMN_ENTRY_FEE,
    DK_COLUMN_WINNINGS,
    DK_COLUMN_SPORT,
    DK_COLUMN_DATE,
}


# =============================================================================
# FANDUEL CSV COLUMNS
# =============================================================================

FD_COLUMN_ENTRY_ID = "Entry Id"
FD_COLUMN_CONTEST_NAME = "Contest"
FD_COLUMN_ENTRY_FEE = "Entry Fee"
FD_COLUMN_WINNINGS = "Winnings"
FD_COLUMN_POINTS = "Points"
FD_COLUMN_SPORT = "Sport"
FD_COLUMN_DATE = "Entered"

FD_REQUIRED_COLUMNS: Set[str] = {
    FD_COLUMN_ENTRY_ID,
    FD_COLUMN_CONTEST_NAME,
    FD_COLUMN_ENTRY_FEE,
    FD_COLUMN_WINNINGS,
    FD_COLUMN_SPORT,
    FD_COLUMN_DATE,
}


# =============================================================================
# PERSONA SIGNALS
# =============================================================================
# Each signal is defined as a tuple of (min_value, max_value) for linear
# interpolation. Values below min get score 0, above max get score 1.

# BETTOR signals: Tournament grinder profile
# - High GPP percentage (loves tournaments)
# - Higher avg stakes
# - Low sport diversity (focused)
# - Low multi-entry rate
BETTOR_SIGNALS: Dict[str, Tuple[float, float]] = {
    'gpp_percentage': (0.7, 1.0),       # 70-100% GPP entries
    'avg_entry_fee': (10.0, 999.0),     # $10+ avg stake
    'sport_diversity': (0.0, 0.5),      # Low diversity (inverted)
    'multi_entry_rate': (1.0, 2.0),     # 1-2 entries per contest (inverted)
}

# FANTASY signals: Optimizer/grinder profile
# - High cash percentage (consistent profit)
# - High multi-entry rate (optimizer behavior)
# - High volume
# - Moderate ROI (grinding, not swinging)
FANTASY_SIGNALS: Dict[str, Tuple[float, float]] = {
    'cash_percentage': (0.4, 1.0),      # 40-100% cash entries
    'multi_entry_rate': (3.0, 20.0),    # 3-20 entries per contest
    'entries_per_week': (20.0, 100.0),  # 20+ entries/week
    'roi_moderate': (-20.0, 20.0),      # -20% to +20% ROI (special handling)
}

# STATS_NERD signals: Researcher profile
# - High sport diversity (explores)
# - High stake variance (experiments)
# - Lower avg stakes (testing theories, not maximizing profit)
STATS_NERD_SIGNALS: Dict[str, Tuple[float, float]] = {
    'sport_diversity': (0.7, 1.0),      # 70-100% diverse
    'stake_variance': (0.5, 2.0),       # High variance
    'avg_entry_fee': (0.0, 5.0),        # $0-5 avg stake (inverted for high stakes)
}


# =============================================================================
# PATTERN MODIFIERS BY PERSONA
# =============================================================================
# These define how each persona prioritizes different pattern types.
# Values > 1.0 = prioritize, < 1.0 = deprioritize

BETTOR_MODIFIERS: Dict[str, Decimal] = {
    'line_movement': Decimal('1.5'),
    'historical_trends': Decimal('0.9'),
    'injury_impact': Decimal('1.3'),
    'weather_factors': Decimal('0.8'),
    'player_correlations': Decimal('0.7'),
    'situational_stats': Decimal('1.0'),
    'live_odds_delta': Decimal('1.4'),
    'contrarian_plays': Decimal('1.1'),
}

FANTASY_MODIFIERS: Dict[str, Decimal] = {
    'line_movement': Decimal('0.8'),
    'historical_trends': Decimal('1.1'),
    'injury_impact': Decimal('1.5'),
    'weather_factors': Decimal('1.0'),
    'player_correlations': Decimal('1.6'),
    'situational_stats': Decimal('1.3'),
    'live_odds_delta': Decimal('0.6'),
    'contrarian_plays': Decimal('1.4'),
}

STATS_NERD_MODIFIERS: Dict[str, Decimal] = {
    'line_movement': Decimal('0.7'),
    'historical_trends': Decimal('1.5'),
    'injury_impact': Decimal('0.9'),
    'weather_factors': Decimal('1.3'),
    'player_correlations': Decimal('1.2'),
    'situational_stats': Decimal('1.6'),
    'live_odds_delta': Decimal('0.5'),
    'contrarian_plays': Decimal('1.3'),
}


# =============================================================================
# BEHAVIORAL CALCULATION CONSTANTS
# =============================================================================

# Shannon entropy normalization
# Max theoretical entropy for N sports = log2(N)
# We use max observed sports for normalization

# Exponential decay half-life for recency scoring
RECENCY_HALF_LIFE_DAYS = 90

# Confidence score weights
CONFIDENCE_WEIGHT_VOLUME = Decimal('0.5')    # Entry count factor
CONFIDENCE_WEIGHT_RECENCY = Decimal('0.3')   # Recency factor
CONFIDENCE_WEIGHT_DIVERSITY = Decimal('0.2') # Contest diversity factor

# Minimum entries for full confidence
MIN_ENTRIES_FOR_FULL_CONFIDENCE = 50

# Days until data is considered stale
STALE_DATA_THRESHOLD_DAYS = 365


# =============================================================================
# PERSONA DETECTION
# =============================================================================

# Threshold for considering a persona score significant (for hybrid detection)
HYBRID_THRESHOLD = Decimal('0.3')


# =============================================================================
# DATE FORMAT PATTERNS
# =============================================================================

# Common date formats encountered in CSV exports
DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",       # 2024-09-15 13:00:00
    "%Y-%m-%d",                 # 2024-09-15
    "%m/%d/%Y %I:%M %p",       # 09/15/2024 1:00 PM
    "%m/%d/%Y",                 # 09/15/2024
    "%b %d, %Y %I:%M%p",       # Sep 15, 2024 1:00PM
    "%b %d, %Y %I:%M %p",      # Sep 15, 2024 1:00 PM
    "%B %d, %Y",                # September 15, 2024
    "%d-%b-%Y",                 # 15-Sep-2024
]


# =============================================================================
# CONTEST CLASSIFICATION PATTERNS
# =============================================================================
# Regex patterns for classifying contest types from names
# Order matters: first match wins

CONTEST_PATTERNS = {
    # Head-to-head contests (check first, most specific)
    CONTEST_H2H: [
        r'\bH2H\b',
        r'\bhead\s*to\s*head\b',
        r'\bheads?\s*up\b',
        r'\b1v1\b',
        r'\bone\s*on\s*one\b',
    ],

    # Cash games (50/50, double-ups)
    CONTEST_CASH: [
        r'\b50/50\b',
        r'\bfifty[\s-]*fifty\b',
        r'\bdouble[\s-]*up\b',
        r'\bcash\s*game\b',
        r'\bsingle[\s-]*entry\b.*\bcash\b',
    ],

    # Multi-entry indicators
    CONTEST_MULTI: [
        r'\b(\d+)[\s-]*max\b',
        r'\bmulti[\s-]*entry\b',
        r'\b\d+[\s-]*entry\b',
        r'\bunlimited\b.*\bentry\b',
    ],

    # GPP/Tournament indicators (check last, most common)
    CONTEST_GPP: [
        r'\bGPP\b',
        r'\btournament\b',
        r'\$[\d,]+K\b',           # Prize pool like $20K, $100K
        r'\bguaranteed\b',
        r'\bGTD\b',
        r'\bmillion\b',
        r'\bfreeroll\b',
        r'\bshowdown\b',
        r'\bclassic\b',
        r'\bshot\b',
        r'\bslate\b',
    ],
}
