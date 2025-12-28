# DFS Behavioral Parser - Claude Code Implementation Specification

## Project Overview

**Purpose:** Parse DraftKings/FanDuel CSV transaction history to auto-detect user personas (Bettor/Fantasy Player/Stats Nerd) and apply weighted pattern detection algorithms for ThirdDownIQ, ShotClockIQ, and PowerPlayIQ sports analytics apps.

**Business Context:**
- Steve is building autonomous revenue stream apps with high margins (99.8% target)
- Users upload their DFS history once, system personalizes their experience
- Reduces friction vs manual persona selection
- Privacy-first: CSVs processed and discarded, only aggregates stored

**Success Metrics:**
- CSV parsing: < 500ms for 10K entries
- Persona detection accuracy: > 85% user satisfaction on manual validation
- Pattern weight application: measurable difference in user engagement by persona
- Zero financial calculation errors (use Decimal throughout)

---

## Technology Stack

**Language:** Python 3.11+
**Key Libraries:**
- `pandas` - CSV parsing and data manipulation
- `dataclasses` - Type-safe data structures
- `decimal` - Precise financial calculations
- `pytest` - Testing framework
- `pydantic` - Data validation
- `sqlalchemy` - Database ORM (PostgreSQL)
- `python-dateutil` - Flexible date parsing

**Database:** PostgreSQL 15+
**Deployment:** TBD (initially local development)

---

## Project Structure

```
dfs_behavioral_parser/
├── README.md
├── requirements.txt
├── setup.py
├── .env.example
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── sample_draftkings.csv
│   │   ├── sample_fanduel.csv
│   │   ├── sample_mixed_data.csv
│   │   └── sample_edge_cases.csv
│   ├── unit/
│   │   ├── test_parsers.py
│   │   ├── test_classifiers.py
│   │   ├── test_scoring.py
│   │   └── test_detection.py
│   └── integration/
│       ├── test_end_to_end.py
│       └── test_profile_persistence.py
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── dfs_entry.py
│   │   ├── behavioral_metrics.py
│   │   ├── persona_score.py
│   │   ├── pattern_weights.py
│   │   └── user_profile.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py
│   │   ├── draftkings_parser.py
│   │   ├── fanduel_parser.py
│   │   └── platform_detector.py
│   ├── classifiers/
│   │   ├── __init__.py
│   │   └── contest_type_classifier.py
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── behavioral_scorer.py
│   │   ├── persona_detector.py
│   │   └── weight_mapper.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── profile_repository.py
│   └── utils/
│       ├── __init__.py
│       ├── csv_validator.py
│       ├── date_parser.py
│       └── constants.py
└── scripts/
    ├── init_db.py
    └── sample_data_generator.py
```

---

## Phase 1: Foundation & Data Models

### Objective
Establish core data structures and validation logic before any parsing.

### Files to Create

#### 1.1 `src/models/dfs_entry.py`

**Purpose:** Normalized representation of a single DFS contest entry.

**Implementation Requirements:**
```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass
class DFSEntry:
    """
    Normalized DFS contest entry from any platform.
    
    Why Decimal for money:
    - Avoids floating point errors (0.1 + 0.2 != 0.3)
    - Accounting standard for financial calculations
    - Maintains precision for tax reporting
    """
    entry_id: str
    date: datetime
    sport: str                    # Uppercase: NFL, NBA, NHL, MLB, etc.
    contest_type: str             # GPP, CASH, H2H, MULTI, UNKNOWN
    entry_fee: Decimal
    winnings: Decimal
    points: Decimal
    source: str                   # "DRAFTKINGS" | "FANDUEL"
    contest_name: Optional[str] = None  # Preserve for debugging
    
    def __post_init__(self):
        """Validate data after initialization"""
        if self.entry_fee < 0:
            raise ValueError(f"Entry fee cannot be negative: {self.entry_fee}")
        if self.winnings < 0:
            raise ValueError(f"Winnings cannot be negative: {self.winnings}")
        if self.source not in ["DRAFTKINGS", "FANDUEL"]:
            raise ValueError(f"Invalid source: {self.source}")
        
        # Normalize sport to uppercase
        self.sport = self.sport.upper()
    
    @property
    def roi(self) -> Decimal:
        """Return on investment as percentage"""
        if self.entry_fee == 0:
            return Decimal('0')
        return ((self.winnings - self.entry_fee) / self.entry_fee) * 100
    
    @property
    def profit(self) -> Decimal:
        """Net profit/loss for this entry"""
        return self.winnings - self.entry_fee
    
    @property
    def is_winning_entry(self) -> bool:
        """Did this entry profit?"""
        return self.winnings > self.entry_fee
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/API"""
        return {
            'entry_id': self.entry_id,
            'date': self.date.isoformat(),
            'sport': self.sport,
            'contest_type': self.contest_type,
            'entry_fee': str(self.entry_fee),
            'winnings': str(self.winnings),
            'points': str(self.points),
            'source': self.source,
            'contest_name': self.contest_name,
            'roi': str(self.roi),
            'profit': str(self.profit),
        }
```

**Tests Required:**
- Validate negative fee/winnings rejection
- Validate invalid source rejection
- Verify ROI calculation (including zero-fee edge case)
- Verify profit calculation
- Test sport normalization (lowercase → uppercase)
- Test to_dict() serialization

**Acceptance Criteria:**
- [ ] All properties return correct types
- [ ] Validation errors raise with clear messages
- [ ] ROI formula matches: `((W - F) / F) * 100`
- [ ] Decimal precision maintained (no float conversion)

---

#### 1.2 `src/models/behavioral_metrics.py`

**Purpose:** Aggregated behavioral indicators from entry history.

**Implementation Requirements:**
```python
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict

@dataclass
class BehavioralMetrics:
    """
    Aggregated metrics from DFS entry history.
    
    Why these metrics:
    - Volume patterns reveal commitment level
    - Financial patterns reveal risk tolerance
    - Sport/contest distribution reveals specialization vs exploration
    - Temporal patterns reveal activity consistency
    """
    
    # Volume metrics
    total_entries: int = 0
    entries_by_sport: Dict[str, int] = field(default_factory=dict)
    entries_by_contest_type: Dict[str, int] = field(default_factory=dict)
    
    # Financial metrics
    total_invested: Decimal = Decimal('0')
    total_winnings: Decimal = Decimal('0')
    avg_entry_fee: Decimal = Decimal('0')
    roi_overall: Decimal = Decimal('0')
    
    # Behavior patterns (0.0 to 1.0 scale)
    gpp_percentage: Decimal = Decimal('0')      # % of entries in GPP tournaments
    cash_percentage: Decimal = Decimal('0')     # % of entries in cash games
    h2h_percentage: Decimal = Decimal('0')      # % of entries in head-to-head
    multi_entry_rate: Decimal = Decimal('0')    # Avg entries per unique contest
    sport_diversity: Decimal = Decimal('0')     # Shannon entropy (0=focused, 1=diverse)
    stake_variance: Decimal = Decimal('0')      # Coefficient of variation in entry fees
    
    # Temporal patterns
    entries_per_week: Decimal = Decimal('0')
    most_active_day: str = ""                   # Monday, Tuesday, etc.
    recency_score: Decimal = Decimal('0')       # Exponential decay weight
    
    # Data quality
    confidence_score: Decimal = Decimal('0')    # 0.0 to 1.0 based on data completeness
    
    def to_dict(self) -> dict:
        """Serialize for storage"""
        return {
            'total_entries': self.total_entries,
            'entries_by_sport': self.entries_by_sport,
            'entries_by_contest_type': self.entries_by_contest_type,
            'total_invested': str(self.total_invested),
            'total_winnings': str(self.total_winnings),
            'avg_entry_fee': str(self.avg_entry_fee),
            'roi_overall': str(self.roi_overall),
            'gpp_percentage': str(self.gpp_percentage),
            'cash_percentage': str(self.cash_percentage),
            'h2h_percentage': str(self.h2h_percentage),
            'multi_entry_rate': str(self.multi_entry_rate),
            'sport_diversity': str(self.sport_diversity),
            'stake_variance': str(self.stake_variance),
            'entries_per_week': str(self.entries_per_week),
            'most_active_day': self.most_active_day,
            'recency_score': str(self.recency_score),
            'confidence_score': str(self.confidence_score),
        }
```

**Tests Required:**
- Validate default initialization
- Test to_dict() serialization
- Verify all percentages stay 0.0 to 1.0 range

**Acceptance Criteria:**
- [ ] All Decimal fields initialize properly
- [ ] Dict fields use default_factory (avoid mutable default trap)
- [ ] Serialization preserves precision

---

#### 1.3 `src/models/persona_score.py`

**Purpose:** Confidence scores for each persona type.

**Implementation Requirements:**
```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple

@dataclass
class PersonaScore:
    """
    Confidence scores for user persona classification.
    
    Why weighted approach:
    - Users rarely pure archetypes
    - Hybrid personas common (e.g., Bettor+Fantasy)
    - Allows proportional weight blending
    """
    bettor: Decimal = Decimal('0')        # 0.0 to 1.0
    fantasy: Decimal = Decimal('0')       # 0.0 to 1.0
    stats_nerd: Decimal = Decimal('0')    # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate scores in valid range"""
        for field_name in ['bettor', 'fantasy', 'stats_nerd']:
            score = getattr(self, field_name)
            if not (Decimal('0') <= score <= Decimal('1')):
                raise ValueError(f"{field_name} score must be 0.0-1.0, got {score}")
    
    @property
    def primary_persona(self) -> str:
        """Return highest scoring persona"""
        scores = {
            'BETTOR': self.bettor,
            'FANTASY': self.fantasy,
            'STATS_NERD': self.stats_nerd,
        }
        return max(scores, key=scores.get)
    
    @property
    def is_hybrid(self) -> bool:
        """True if multiple personas score > 0.3"""
        high_scores = sum(1 for s in [self.bettor, self.fantasy, self.stats_nerd] 
                          if s > Decimal('0.3'))
        return high_scores >= 2
    
    @property
    def confidence(self) -> Decimal:
        """Confidence in classification (0.0 to 1.0)"""
        max_score = max(self.bettor, self.fantasy, self.stats_nerd)
        min_score = min(self.bettor, self.fantasy, self.stats_nerd)
        # Higher spread = higher confidence
        return max_score - min_score
    
    def get_sorted_personas(self) -> list[Tuple[str, Decimal]]:
        """Return personas sorted by score, descending"""
        return sorted([
            ('BETTOR', self.bettor),
            ('FANTASY', self.fantasy),
            ('STATS_NERD', self.stats_nerd),
        ], key=lambda x: x[1], reverse=True)
    
    def to_dict(self) -> dict:
        return {
            'bettor': str(self.bettor),
            'fantasy': str(self.fantasy),
            'stats_nerd': str(self.stats_nerd),
            'primary_persona': self.primary_persona,
            'is_hybrid': self.is_hybrid,
            'confidence': str(self.confidence),
        }
```

**Tests Required:**
- Validate score range enforcement (reject < 0 or > 1)
- Test primary_persona with various score combinations
- Test is_hybrid threshold logic
- Test confidence calculation
- Test get_sorted_personas() ordering

**Acceptance Criteria:**
- [ ] Invalid scores raise ValueError
- [ ] Primary persona always returns highest
- [ ] Hybrid detection works at 0.3 threshold
- [ ] Confidence formula correct: `max - min`

---

#### 1.4 `src/models/pattern_weights.py`

**Purpose:** Multipliers for pattern detection algorithms.

**Implementation Requirements:**
```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class PatternWeights:
    """
    Multipliers applied to pattern detection algorithms.
    
    Why these patterns:
    - line_movement: Betting market shifts (Bettor priority)
    - historical_trends: Long-term statistical patterns (Stats Nerd priority)
    - injury_impact: News-driven lineup changes (Fantasy priority)
    - weather_factors: Environmental variables (Stats Nerd)
    - player_correlations: Stacking strategies (Fantasy priority)
    - situational_stats: Context-specific performance (Stats Nerd)
    - live_odds_delta: Real-time line shopping (Bettor priority)
    - contrarian_plays: Low-ownership opportunities (Fantasy/Stats)
    """
    line_movement: Decimal = Decimal('1.0')
    historical_trends: Decimal = Decimal('1.0')
    injury_impact: Decimal = Decimal('1.0')
    weather_factors: Decimal = Decimal('1.0')
    player_correlations: Decimal = Decimal('1.0')
    situational_stats: Decimal = Decimal('1.0')
    live_odds_delta: Decimal = Decimal('1.0')
    contrarian_plays: Decimal = Decimal('1.0')
    
    def __post_init__(self):
        """Validate all weights are positive"""
        for field in self.__dataclass_fields__:
            weight = getattr(self, field)
            if weight < 0:
                raise ValueError(f"Weight {field} cannot be negative: {weight}")
    
    def apply_to_score(self, pattern_name: str, base_score: Decimal) -> Decimal:
        """Apply weight to a base pattern score"""
        if not hasattr(self, pattern_name):
            raise ValueError(f"Unknown pattern: {pattern_name}")
        weight = getattr(self, pattern_name)
        return base_score * weight
    
    def to_dict(self) -> dict:
        return {field: str(getattr(self, field)) 
                for field in self.__dataclass_fields__}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PatternWeights':
        """Create from dictionary (e.g., from database)"""
        return cls(**{k: Decimal(v) for k, v in data.items()})
```

**Tests Required:**
- Validate negative weight rejection
- Test apply_to_score() calculation
- Test to_dict() / from_dict() round-trip
- Test unknown pattern name handling

**Acceptance Criteria:**
- [ ] All weights default to 1.0 (neutral)
- [ ] Negative weights rejected
- [ ] apply_to_score() returns base * weight
- [ ] Serialization preserves precision

---

#### 1.5 `src/utils/constants.py`

**Purpose:** Centralized configuration and magic numbers.

**Implementation Requirements:**
```python
from decimal import Decimal

# Platform identifiers
PLATFORM_DRAFTKINGS = "DRAFTKINGS"
PLATFORM_FANDUEL = "FANDUEL"

# Contest type classifications
CONTEST_TYPE_GPP = "GPP"          # Guaranteed Prize Pool tournaments
CONTEST_TYPE_CASH = "CASH"        # Cash games (50/50, Double Up)
CONTEST_TYPE_H2H = "H2H"          # Head to Head
CONTEST_TYPE_MULTI = "MULTI"      # Multiplier/3-max/5-max
CONTEST_TYPE_UNKNOWN = "UNKNOWN"

# Sports normalization
SPORT_MAPPINGS = {
    'NFL': 'NFL',
    'FOOTBALL': 'NFL',
    'NBA': 'NBA',
    'BASKETBALL': 'NBA',
    'NHL': 'NHL',
    'HOCKEY': 'NHL',
    'MLB': 'MLB',
    'BASEBALL': 'MLB',
    'PGA': 'PGA',
    'GOLF': 'PGA',
    'SOCCER': 'SOCCER',
    'MMA': 'MMA',
    'UFC': 'MMA',
    'NASCAR': 'NASCAR',
    'TENNIS': 'TENNIS',
    'LOL': 'LOL',
    'CSGO': 'CSGO',
    'DOTA2': 'DOTA2',
}

# Data quality thresholds
MIN_ENTRIES_FOR_CONFIDENCE = 50    # Below this = low confidence
MIN_ENTRIES_FOR_PERSONA = 20       # Minimum for persona detection
MAX_DATA_AGE_DAYS = 730           # 2 years; older data less relevant

# Persona detection thresholds
HYBRID_THRESHOLD = Decimal('0.3')  # Multiple personas > this = hybrid
HIGH_CONFIDENCE_THRESHOLD = Decimal('0.6')  # Single persona > this = confident

# Contest type pattern matching (regex patterns)
GPP_PATTERNS = [
    r'\$[\d,]+',           # Dollar amounts: "$20K", "$100,000"
    r'milly|million',      # "Sunday Million"
    r'shot|sharpshooter',  # "Millionaire Maker Shot"
    r'gtd|guaranteed',     # "$10K GTD"
    r'maker',              # "Millionaire Maker"
    r'playoff|championship',  # "Playoff Challenge"
    r'satellite|qualifier',   # Tournament qualifiers
]

CASH_PATTERNS = [
    r'double.?up',         # "Double Up"
    r'50/50',              # "50/50"
    r'cash',               # "Cash Game"
]

H2H_PATTERNS = [
    r'head.?to.?head|h2h', # "Head to Head"
]

MULTI_PATTERNS = [
    r'\d+-max',            # "3-max", "5-max"
    r'multiplier',         # "Multiplier"
]

# DraftKings CSV columns
DK_COLUMNS = [
    'Entry ID',
    'Contest Name',
    'Contest ID',
    'Entry Fee',
    'Winnings',
    'Sport',
    'Date Entered',
    'Points',
]

# FanDuel CSV columns
FD_COLUMNS = [
    'Entry ID',
    'Contest',
    'Entry Fee',
    'Winnings',
    'Points',
    'Sport',
    'Entered',
]

# Persona scoring weights (used in PersonaDetector)
BETTOR_SIGNALS = {
    'gpp_percentage': (Decimal('0.7'), Decimal('1.0')),
    'avg_entry_fee': (Decimal('10.0'), Decimal('999999')),
    'sport_diversity': (Decimal('0.0'), Decimal('0.5')),
    'multi_entry_rate': (Decimal('1.0'), Decimal('2.0')),
}

FANTASY_SIGNALS = {
    'cash_percentage': (Decimal('0.4'), Decimal('1.0')),
    'multi_entry_rate': (Decimal('3.0'), Decimal('999999')),
    'entries_per_week': (Decimal('20.0'), Decimal('999999')),
    'roi_overall': (Decimal('-20.0'), Decimal('20.0')),
}

STATS_NERD_SIGNALS = {
    'sport_diversity': (Decimal('0.7'), Decimal('1.0')),
    'stake_variance': (Decimal('0.5'), Decimal('999999')),
    'avg_entry_fee': (Decimal('0.0'), Decimal('5.0')),
}

# Pattern weight modifiers by persona
BETTOR_MODIFIERS = {
    'line_movement': Decimal('1.5'),
    'historical_trends': Decimal('0.9'),
    'injury_impact': Decimal('1.3'),
    'weather_factors': Decimal('1.0'),
    'player_correlations': Decimal('0.7'),
    'situational_stats': Decimal('1.0'),
    'live_odds_delta': Decimal('1.4'),
    'contrarian_plays': Decimal('0.8'),
}

FANTASY_MODIFIERS = {
    'line_movement': Decimal('0.8'),
    'historical_trends': Decimal('1.0'),
    'injury_impact': Decimal('1.5'),
    'weather_factors': Decimal('1.1'),
    'player_correlations': Decimal('1.6'),
    'situational_stats': Decimal('1.3'),
    'live_odds_delta': Decimal('0.6'),
    'contrarian_plays': Decimal('1.2'),
}

STATS_NERD_MODIFIERS = {
    'line_movement': Decimal('1.0'),
    'historical_trends': Decimal('1.5'),
    'injury_impact': Decimal('1.0'),
    'weather_factors': Decimal('1.3'),
    'player_correlations': Decimal('1.4'),
    'situational_stats': Decimal('1.6'),
    'live_odds_delta': Decimal('0.7'),
    'contrarian_plays': Decimal('1.3'),
}
```

**Tests Required:**
- Validate all constants are correct types
- Test SPORT_MAPPINGS coverage for common variations

**Acceptance Criteria:**
- [ ] All Decimal constants use proper precision
- [ ] Pattern lists are non-empty
- [ ] Column lists match actual CSV formats

---

### Phase 1 Checkpoint

**Before proceeding to Phase 2:**
- [ ] All model classes created
- [ ] All unit tests passing
- [ ] Type hints complete
- [ ] Docstrings explain "why" not just "what"

---

## Phase 2: CSV Parsing & Classification

### Objective
Implement platform-specific parsers and contest type classification.

### Files to Create

#### 2.1 `src/parsers/platform_detector.py`

**Purpose:** Detect DraftKings vs FanDuel from CSV headers.

**Implementation Requirements:**
```python
from typing import List
from src.utils.constants import (
    PLATFORM_DRAFTKINGS, 
    PLATFORM_FANDUEL,
    DK_COLUMNS,
    FD_COLUMNS
)

class PlatformDetector:
    """
    Identify platform from CSV column headers.
    
    Why separate detector:
    - User might upload wrong file
    - Better error messages than generic parse failure
    - Allows future platform additions without parser changes
    """
    
    @staticmethod
    def detect(columns: List[str]) -> str:
        """
        Detect platform from CSV columns.
        
        Args:
            columns: List of column headers from CSV
            
        Returns:
            PLATFORM_DRAFTKINGS or PLATFORM_FANDUEL
            
        Raises:
            ValueError: If platform cannot be determined
        """
        columns_normalized = [col.strip() for col in columns]
        
        # Check DraftKings signature columns
        dk_match = all(col in columns_normalized for col in DK_COLUMNS[:5])
        
        # Check FanDuel signature columns
        fd_match = all(col in columns_normalized for col in FD_COLUMNS[:5])
        
        if dk_match and not fd_match:
            return PLATFORM_DRAFTKINGS
        elif fd_match and not dk_match:
            return PLATFORM_FANDUEL
        elif dk_match and fd_match:
            # Disambiguate using unique columns
            if 'Contest ID' in columns_normalized:
                return PLATFORM_DRAFTKINGS
            else:
                return PLATFORM_FANDUEL
        else:
            raise ValueError(
                f"Cannot detect platform from columns: {columns_normalized}. "
                f"Expected DraftKings columns: {DK_COLUMNS} "
                f"or FanDuel columns: {FD_COLUMNS}"
            )
```

**Tests Required:**
- Test DraftKings CSV detection
- Test FanDuel CSV detection
- Test ambiguous/invalid CSV rejection
- Test column whitespace handling

**Acceptance Criteria:**
- [ ] Correctly identifies DK vs FD
- [ ] Raises clear error on unknown format
- [ ] Handles column name variations (case, whitespace)

---

#### 2.2 `src/parsers/base_parser.py`

**Purpose:** Abstract base class for platform parsers.

**Implementation Requirements:**
```python
from abc import ABC, abstractmethod
from typing import List
from decimal import Decimal
from datetime import datetime
import pandas as pd

from src.models.dfs_entry import DFSEntry

class BaseParser(ABC):
    """
    Abstract base class for platform-specific CSV parsers.
    
    Why abstract base:
    - Enforces consistent interface across platforms
    - Shared validation logic
    - Easy to add new platforms (e.g., Yahoo, FantasyDraft)
    """
    
    def parse_csv(self, file_path: str) -> List[DFSEntry]:
        """
        Main entry point for parsing.
        
        Template method pattern:
        1. Read CSV
        2. Validate structure
        3. Parse rows (platform-specific)
        4. Validate entries
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of normalized DFSEntry objects
        """
        df = pd.read_csv(file_path)
        self._validate_columns(df)
        entries = self._parse_rows(df)
        self._validate_entries(entries)
        return entries
    
    @abstractmethod
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate CSV has required columns"""
        pass
    
    @abstractmethod
    def _parse_rows(self, df: pd.DataFrame) -> List[DFSEntry]:
        """Parse DataFrame rows into DFSEntry objects"""
        pass
    
    def _validate_entries(self, entries: List[DFSEntry]) -> None:
        """
        Validate parsed entries meet business rules.
        
        Why separate validation:
        - Catch data quality issues early
        - Provide clear error messages
        - Prevent garbage-in-garbage-out
        """
        if len(entries) == 0:
            raise ValueError("No valid entries found in CSV")
        
        # Check for duplicate entry IDs
        entry_ids = [e.entry_id for e in entries]
        duplicates = set([x for x in entry_ids if entry_ids.count(x) > 1])
        if duplicates:
            raise ValueError(f"Duplicate entry IDs found: {duplicates}")
    
    @staticmethod
    def _clean_currency(value: str) -> Decimal:
        """
        Convert currency string to Decimal.
        
        Examples:
            "$5.00" -> Decimal('5.00')
            "$1,234.56" -> Decimal('1234.56')
            "0" -> Decimal('0.00')
        """
        if pd.isna(value) or value == '':
            return Decimal('0.00')
        
        # Remove $, commas, whitespace
        cleaned = str(value).replace('$', '').replace(',', '').strip()
        
        try:
            return Decimal(cleaned)
        except:
            raise ValueError(f"Cannot convert to currency: {value}")
    
    @staticmethod
    def _clean_points(value) -> Decimal:
        """Convert points string to Decimal"""
        if pd.isna(value) or value == '':
            return Decimal('0.00')
        
        cleaned = str(value).replace(',', '').strip()
        
        try:
            return Decimal(cleaned)
        except:
            raise ValueError(f"Cannot convert to points: {value}")
```

**Tests Required:**
- Test _clean_currency() with various formats
- Test _clean_points() with various formats
- Test _validate_entries() duplicate detection
- Test parse_csv() template method flow

**Acceptance Criteria:**
- [ ] Currency parsing handles $, commas, whitespace
- [ ] Points parsing handles decimals correctly
- [ ] Duplicate detection works
- [ ] Template method enforces subclass implementation

---

#### 2.3 `src/parsers/draftkings_parser.py`

**Purpose:** Parse DraftKings CSV format.

**Implementation Requirements:**
```python
from typing import List
from datetime import datetime
import pandas as pd

from src.parsers.base_parser import BaseParser
from src.models.dfs_entry import DFSEntry
from src.utils.constants import PLATFORM_DRAFTKINGS, DK_COLUMNS
from src.utils.date_parser import parse_flexible_date

class DraftKingsParser(BaseParser):
    """
    Parser for DraftKings CSV export format.
    
    Expected columns:
    - Entry ID
    - Contest Name
    - Contest ID
    - Entry Fee
    - Winnings
    - Sport
    - Date Entered
    - Points
    """
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Ensure all required columns present"""
        missing = set(DK_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required DraftKings columns: {missing}")
    
    def _parse_rows(self, df: pd.DataFrame) -> List[DFSEntry]:
        """Parse DataFrame into DFSEntry objects"""
        entries = []
        
        for idx, row in df.iterrows():
            try:
                entry = DFSEntry(
                    entry_id=str(row['Entry ID']),
                    contest_name=str(row['Contest Name']),
                    date=parse_flexible_date(row['Date Entered']),
                    sport=str(row['Sport']),
                    contest_type='UNKNOWN',  # Classified later
                    entry_fee=self._clean_currency(row['Entry Fee']),
                    winnings=self._clean_currency(row['Winnings']),
                    points=self._clean_points(row['Points']),
                    source=PLATFORM_DRAFTKINGS,
                )
                entries.append(entry)
            except Exception as e:
                # Log warning but continue parsing
                print(f"Warning: Skipping row {idx}: {e}")
                continue
        
        return entries
```

**Tests Required:**
- Test with sample_draftkings.csv
- Test column validation
- Test row skipping on parse errors
- Test date parsing

**Acceptance Criteria:**
- [ ] Parses valid DK CSV correctly
- [ ] Rejects CSV missing required columns
- [ ] Skips malformed rows with warning
- [ ] All currency/points cleaned properly

---

#### 2.4 `src/parsers/fanduel_parser.py`

**Purpose:** Parse FanDuel CSV format.

**Implementation Requirements:**
```python
from typing import List
from datetime import datetime
import pandas as pd

from src.parsers.base_parser import BaseParser
from src.models.dfs_entry import DFSEntry
from src.utils.constants import PLATFORM_FANDUEL, FD_COLUMNS
from src.utils.date_parser import parse_flexible_date

class FanDuelParser(BaseParser):
    """
    Parser for FanDuel CSV export format.
    
    Expected columns:
    - Entry ID
    - Contest
    - Entry Fee
    - Winnings
    - Points
    - Sport
    - Entered
    
    Note: FanDuel date format varies:
    - "Sep 17, 2024 1:00PM"
    - "September 17, 2024 13:00"
    """
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Ensure all required columns present"""
        missing = set(FD_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required FanDuel columns: {missing}")
    
    def _parse_rows(self, df: pd.DataFrame) -> List[DFSEntry]:
        """Parse DataFrame into DFSEntry objects"""
        entries = []
        
        for idx, row in df.iterrows():
            try:
                entry = DFSEntry(
                    entry_id=str(row['Entry ID']),
                    contest_name=str(row['Contest']),
                    date=parse_flexible_date(row['Entered']),
                    sport=str(row['Sport']),
                    contest_type='UNKNOWN',  # Classified later
                    entry_fee=self._clean_currency(row['Entry Fee']),
                    winnings=self._clean_currency(row['Winnings']),
                    points=self._clean_points(row['Points']),
                    source=PLATFORM_FANDUEL,
                )
                entries.append(entry)
            except Exception as e:
                print(f"Warning: Skipping row {idx}: {e}")
                continue
        
        return entries
```

**Tests Required:**
- Test with sample_fanduel.csv
- Test column validation
- Test FD date format variations
- Test row skipping

**Acceptance Criteria:**
- [ ] Parses valid FD CSV correctly
- [ ] Handles FD date format variants
- [ ] Rejects CSV missing required columns
- [ ] Skips malformed rows with warning

---

#### 2.5 `src/utils/date_parser.py`

**Purpose:** Flexible date parsing for various formats.

**Implementation Requirements:**
```python
from datetime import datetime
from dateutil import parser as dateutil_parser

def parse_flexible_date(date_str: str) -> datetime:
    """
    Parse date string in various formats.
    
    Handles:
    - ISO 8601: "2024-09-15T13:00:00"
    - DraftKings: "2024-09-15 13:00:00"
    - FanDuel: "Sep 17, 2024 1:00PM"
    - FanDuel alt: "September 17, 2024 13:00"
    
    Args:
        date_str: Date string in any supported format
        
    Returns:
        datetime object
        
    Raises:
        ValueError: If date cannot be parsed
    """
    if not date_str or str(date_str).strip() == '':
        raise ValueError("Empty date string")
    
    try:
        # dateutil.parser handles most formats automatically
        return dateutil_parser.parse(str(date_str))
    except Exception as e:
        raise ValueError(f"Cannot parse date: {date_str}. Error: {e}")
```

**Tests Required:**
- Test ISO 8601 format
- Test DraftKings format
- Test FanDuel formats (multiple variants)
- Test invalid date rejection
- Test empty string handling

**Acceptance Criteria:**
- [ ] Parses all documented formats
- [ ] Raises ValueError on unparseable dates
- [ ] Returns timezone-aware datetime if possible

---

#### 2.6 `src/classifiers/contest_type_classifier.py`

**Purpose:** Classify contest type from contest name.

**Implementation Requirements:**
```python
import re
from typing import List
from src.utils.constants import (
    CONTEST_TYPE_GPP,
    CONTEST_TYPE_CASH,
    CONTEST_TYPE_H2H,
    CONTEST_TYPE_MULTI,
    CONTEST_TYPE_UNKNOWN,
    GPP_PATTERNS,
    CASH_PATTERNS,
    H2H_PATTERNS,
    MULTI_PATTERNS,
)

class ContestTypeClassifier:
    """
    Classify contest type from contest name using pattern matching.
    
    Why pattern-based:
    - Platform naming inconsistent
    - New contest types appear regularly
    - Easy to update patterns vs retraining ML model
    
    Priority order (most specific first):
    1. H2H (head to head is very specific)
    2. CASH (specific game types)
    3. MULTI (multiplier games)
    4. GPP (catch-all for tournaments)
    """
    
    def __init__(self):
        # Compile patterns for performance
        self.h2h_regex = self._compile_patterns(H2H_PATTERNS)
        self.cash_regex = self._compile_patterns(CASH_PATTERNS)
        self.multi_regex = self._compile_patterns(MULTI_PATTERNS)
        self.gpp_regex = self._compile_patterns(GPP_PATTERNS)
    
    def _compile_patterns(self, patterns: List[str]) -> re.Pattern:
        """Combine patterns into single regex"""
        combined = '|'.join(patterns)
        return re.compile(combined, re.IGNORECASE)
    
    def classify(self, contest_name: str) -> str:
        """
        Classify contest type from name.
        
        Args:
            contest_name: Contest name string
            
        Returns:
            Contest type constant
        """
        if not contest_name:
            return CONTEST_TYPE_UNKNOWN
        
        name_lower = contest_name.lower()
        
        # Check in priority order
        if self.h2h_regex.search(name_lower):
            return CONTEST_TYPE_H2H
        
        if self.cash_regex.search(name_lower):
            return CONTEST_TYPE_CASH
        
        if self.multi_regex.search(name_lower):
            return CONTEST_TYPE_MULTI
        
        if self.gpp_regex.search(name_lower):
            return CONTEST_TYPE_GPP
        
        return CONTEST_TYPE_UNKNOWN
    
    def classify_batch(self, contest_names: List[str]) -> List[str]:
        """Classify multiple contest names efficiently"""
        return [self.classify(name) for name in contest_names]
```

**Tests Required:**
- Test H2H pattern matching
- Test CASH pattern matching
- Test MULTI pattern matching
- Test GPP pattern matching
- Test UNKNOWN fallback
- Test priority order (H2H > CASH > MULTI > GPP)
- Test case insensitivity
- Test batch classification

**Acceptance Criteria:**
- [ ] All patterns match expected contest names
- [ ] Priority order enforced correctly
- [ ] Unknown contests default to UNKNOWN
- [ ] Batch processing works efficiently

---

### Phase 2 Checkpoint

**Before proceeding to Phase 3:**
- [ ] Both parsers created and tested
- [ ] Platform detection works
- [ ] Contest classification works
- [ ] Date parsing handles all formats
- [ ] Integration test: Parse sample CSV end-to-end

**Integration Test Spec:**
```python
def test_parse_draftkings_end_to_end():
    """Test complete DK parsing pipeline"""
    # 1. Detect platform
    detector = PlatformDetector()
    with open('fixtures/sample_draftkings.csv') as f:
        columns = f.readline().strip().split(',')
    assert detector.detect(columns) == PLATFORM_DRAFTKINGS
    
    # 2. Parse CSV
    parser = DraftKingsParser()
    entries = parser.parse_csv('fixtures/sample_draftkings.csv')
    assert len(entries) > 0
    
    # 3. Classify contests
    classifier = ContestTypeClassifier()
    for entry in entries:
        entry.contest_type = classifier.classify(entry.contest_name)
    
    # 4. Validate results
    assert all(e.contest_type != CONTEST_TYPE_UNKNOWN for e in entries)
    assert all(isinstance(e.entry_fee, Decimal) for e in entries)
```

---

## Phase 3: Behavioral Scoring & Persona Detection

### Objective
Calculate behavioral metrics and detect user personas.

### Files to Create

#### 3.1 `src/scoring/behavioral_scorer.py`

**Purpose:** Calculate aggregated metrics from entry history.

**Implementation Requirements:**
```python
from typing import List, Dict
from decimal import Decimal
from datetime import datetime, timedelta
from collections import Counter
import math

from src.models.dfs_entry import DFSEntry
from src.models.behavioral_metrics import BehavioralMetrics
from src.utils.constants import MIN_ENTRIES_FOR_CONFIDENCE

class BehavioralScorer:
    """
    Calculate behavioral metrics from DFS entry history.
    
    Why these calculations:
    - Reveal user patterns not obvious from raw data
    - Enable persona classification
    - Support personalization decisions
    """
    
    def calculate_metrics(self, entries: List[DFSEntry]) -> BehavioralMetrics:
        """
        Aggregate all behavioral metrics.
        
        Args:
            entries: List of DFSEntry objects
            
        Returns:
            BehavioralMetrics object
        """
        if not entries:
            return BehavioralMetrics()
        
        metrics = BehavioralMetrics()
        
        # Volume metrics
        metrics.total_entries = len(entries)
        metrics.entries_by_sport = self._count_by_sport(entries)
        metrics.entries_by_contest_type = self._count_by_contest_type(entries)
        
        # Financial metrics
        metrics.total_invested = sum(e.entry_fee for e in entries)
        metrics.total_winnings = sum(e.winnings for e in entries)
        metrics.avg_entry_fee = metrics.total_invested / len(entries)
        
        if metrics.total_invested > 0:
            net_profit = metrics.total_winnings - metrics.total_invested
            metrics.roi_overall = (net_profit / metrics.total_invested) * 100
        
        # Behavior patterns
        metrics.gpp_percentage = self._calculate_contest_percentage(
            entries, 'GPP'
        )
        metrics.cash_percentage = self._calculate_contest_percentage(
            entries, 'CASH'
        )
        metrics.h2h_percentage = self._calculate_contest_percentage(
            entries, 'H2H'
        )
        
        metrics.multi_entry_rate = self._calculate_multi_entry_rate(entries)
        metrics.sport_diversity = self._calculate_sport_diversity(entries)
        metrics.stake_variance = self._calculate_stake_variance(entries)
        
        # Temporal patterns
        metrics.entries_per_week = self._calculate_entries_per_week(entries)
        metrics.most_active_day = self._calculate_most_active_day(entries)
        metrics.recency_score = self._calculate_recency_score(entries)
        
        # Data quality
        metrics.confidence_score = self._calculate_confidence_score(entries)
        
        return metrics
    
    def _count_by_sport(self, entries: List[DFSEntry]) -> Dict[str, int]:
        """Count entries by sport"""
        return dict(Counter(e.sport for e in entries))
    
    def _count_by_contest_type(self, entries: List[DFSEntry]) -> Dict[str, int]:
        """Count entries by contest type"""
        return dict(Counter(e.contest_type for e in entries))
    
    def _calculate_contest_percentage(
        self, entries: List[DFSEntry], contest_type: str
    ) -> Decimal:
        """Calculate percentage of entries in specific contest type"""
        count = sum(1 for e in entries if e.contest_type == contest_type)
        return Decimal(count) / Decimal(len(entries))
    
    def _calculate_multi_entry_rate(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate average entries per unique contest.
        
        Why this matters:
        - High multi-entry = optimizer/grinder mentality
        - Low multi-entry = casual/bettor mentality
        """
        # Group by (contest_name, date) to handle same contest across weeks
        contest_keys = [(e.contest_name, e.date.date()) for e in entries]
        unique_contests = len(set(contest_keys))
        
        if unique_contests == 0:
            return Decimal('1.0')
        
        return Decimal(len(entries)) / Decimal(unique_contests)
    
    def _calculate_sport_diversity(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate Shannon entropy of sport distribution.
        
        Formula: H = -Σ(p_i * log2(p_i))
        
        Returns:
            0.0 = focused on one sport
            1.0 = perfectly diverse across all sports
        """
        sport_counts = Counter(e.sport for e in entries)
        total = len(entries)
        
        entropy = 0.0
        for count in sport_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        # Normalize to 0-1 scale
        max_entropy = math.log2(len(sport_counts))
        if max_entropy == 0:
            return Decimal('0')
        
        normalized = entropy / max_entropy
        return Decimal(str(normalized))
    
    def _calculate_stake_variance(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate coefficient of variation in entry fees.
        
        Formula: CV = std_dev / mean
        
        Why this matters:
        - Low variance = consistent stakes (focused strategy)
        - High variance = experimental (stats nerd exploring)
        """
        fees = [float(e.entry_fee) for e in entries]
        
        if not fees or len(fees) < 2:
            return Decimal('0')
        
        mean = sum(fees) / len(fees)
        if mean == 0:
            return Decimal('0')
        
        variance = sum((x - mean) ** 2 for x in fees) / len(fees)
        std_dev = math.sqrt(variance)
        
        cv = std_dev / mean
        return Decimal(str(cv))
    
    def _calculate_entries_per_week(self, entries: List[DFSEntry]) -> Decimal:
        """Calculate average entries per week"""
        if not entries:
            return Decimal('0')
        
        dates = sorted(e.date for e in entries)
        date_range = (dates[-1] - dates[0]).days
        
        if date_range == 0:
            return Decimal(len(entries))
        
        weeks = Decimal(date_range) / Decimal('7')
        return Decimal(len(entries)) / weeks
    
    def _calculate_most_active_day(self, entries: List[DFSEntry]) -> str:
        """Find most common day of week for entries"""
        day_counts = Counter(e.date.strftime('%A') for e in entries)
        if not day_counts:
            return ""
        return day_counts.most_common(1)[0][0]
    
    def _calculate_recency_score(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate exponential decay weight for recent activity.
        
        Why this matters:
        - Recent behavior more predictive than old
        - User preferences evolve over time
        
        Formula: Score = Σ(exp(-days_ago / half_life))
        Half-life: 90 days (3 months)
        """
        if not entries:
            return Decimal('0')
        
        now = datetime.now()
        half_life = 90  # days
        
        total_weight = 0.0
        for entry in entries:
            days_ago = (now - entry.date).days
            weight = math.exp(-days_ago / half_life)
            total_weight += weight
        
        # Normalize to 0-1 scale
        max_possible = len(entries)  # All entries today
        normalized = total_weight / max_possible
        
        return Decimal(str(normalized))
    
    def _calculate_confidence_score(self, entries: List[DFSEntry]) -> Decimal:
        """
        Calculate confidence in metrics based on data quality.
        
        Factors:
        - Number of entries (more = higher confidence)
        - Date range (recent = higher confidence)
        - Contest type coverage (diverse = higher confidence)
        
        Returns: 0.0 to 1.0
        """
        # Factor 1: Entry count
        count_score = min(len(entries) / MIN_ENTRIES_FOR_CONFIDENCE, 1.0)
        
        # Factor 2: Recency (most recent entry < 30 days = 1.0)
        if entries:
            most_recent = max(e.date for e in entries)
            days_old = (datetime.now() - most_recent).days
            recency_score = max(0, 1.0 - (days_old / 365))
        else:
            recency_score = 0.0
        
        # Factor 3: Contest type diversity (4 types = 1.0)
        contest_types = set(e.contest_type for e in entries)
        diversity_score = len(contest_types) / 4.0
        
        # Weighted average
        confidence = (
            0.5 * count_score +
            0.3 * recency_score +
            0.2 * diversity_score
        )
        
        return Decimal(str(confidence))
```

**Tests Required:**
- Test all metric calculations with known inputs
- Test sport diversity (Shannon entropy)
- Test stake variance (coefficient of variation)
- Test multi-entry rate calculation
- Test recency score decay
- Test confidence score factors
- Test edge cases (empty list, single entry, all same sport)

**Acceptance Criteria:**
- [ ] All calculations mathematically correct
- [ ] Shannon entropy normalized to 0-1
- [ ] Confidence score considers all factors
- [ ] Handles edge cases gracefully

---

#### 3.2 `src/scoring/persona_detector.py`

**Purpose:** Score user against persona archetypes.

**Implementation Requirements:**
```python
from decimal import Decimal
from typing import Dict, Tuple

from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.utils.constants import (
    BETTOR_SIGNALS,
    FANTASY_SIGNALS,
    STATS_NERD_SIGNALS,
)

class PersonaDetector:
    """
    Classify user into persona archetypes based on behavioral metrics.
    
    Why weighted scoring:
    - Users rarely pure archetypes
    - Hybrid personas common
    - Allows proportional weight blending in pattern detection
    """
    
    def score_personas(self, metrics: BehavioralMetrics) -> PersonaScore:
        """
        Calculate persona fit scores.
        
        Args:
            metrics: Aggregated behavioral metrics
            
        Returns:
            PersonaScore with 0-1 confidence for each persona
        """
        bettor_score = self._score_persona(metrics, BETTOR_SIGNALS)
        fantasy_score = self._score_persona(metrics, FANTASY_SIGNALS)
        stats_nerd_score = self._score_persona(metrics, STATS_NERD_SIGNALS)
        
        # Normalize scores to sum to 1.0
        total = bettor_score + fantasy_score + stats_nerd_score
        if total > 0:
            bettor_score /= total
            fantasy_score /= total
            stats_nerd_score /= total
        
        return PersonaScore(
            bettor=bettor_score,
            fantasy=fantasy_score,
            stats_nerd=stats_nerd_score,
        )
    
    def _score_persona(
        self,
        metrics: BehavioralMetrics,
        signals: Dict[str, Tuple[Decimal, Decimal]]
    ) -> Decimal:
        """
        Score fit to persona based on signal matching.
        
        Args:
            metrics: User behavioral metrics
            signals: Dict of {metric_name: (min, max)} ranges
            
        Returns:
            Raw score (before normalization)
        """
        total_score = Decimal('0')
        
        for signal_name, (min_val, max_val) in signals.items():
            # Handle nested attributes (e.g., "entries_by_contest_type.MULTI")
            if '.' in signal_name:
                value = self._get_nested_value(metrics, signal_name)
            else:
                value = getattr(metrics, signal_name, Decimal('0'))
            
            # Calculate fit score for this signal
            signal_score = self._score_signal_match(value, min_val, max_val)
            total_score += signal_score
        
        # Average across signals
        return total_score / len(signals)
    
    def _get_nested_value(
        self, metrics: BehavioralMetrics, path: str
    ) -> Decimal:
        """
        Get value from nested dict attribute.
        
        Example: "entries_by_contest_type.MULTI" -> metrics.entries_by_contest_type['MULTI']
        """
        parts = path.split('.')
        attr_name = parts[0]
        key = parts[1] if len(parts) > 1 else None
        
        attr_value = getattr(metrics, attr_name, {})
        
        if key:
            # Get from dict, default to 0 if key missing
            return Decimal(attr_value.get(key, 0))
        else:
            return Decimal(attr_value)
    
    def _score_signal_match(
        self, value: Decimal, min_val: Decimal, max_val: Decimal
    ) -> Decimal:
        """
        Score how well value fits within range.
        
        Linear interpolation:
        - value < min: 0.0
        - value in range: linear 0-1
        - value > max: 1.0
        
        Why linear:
        - Simple, interpretable
        - Avoids overfitting to exact thresholds
        - Easy to tune ranges
        """
        if value < min_val:
            return Decimal('0')
        elif value > max_val:
            return Decimal('1')
        else:
            # Linear interpolation
            range_size = max_val - min_val
            if range_size == 0:
                return Decimal('1')
            return (value - min_val) / range_size
```

**Tests Required:**
- Test Bettor signal matching
- Test Fantasy signal matching
- Test Stats Nerd signal matching
- Test score normalization (sum to 1.0)
- Test nested value extraction
- Test linear interpolation logic
- Test edge cases (all signals at extremes)

**Acceptance Criteria:**
- [ ] Scores always between 0-1
- [ ] Scores sum to 1.0 after normalization
- [ ] Signal matching uses linear interpolation
- [ ] Nested dict access works correctly

---

#### 3.3 `src/scoring/weight_mapper.py`

**Purpose:** Convert persona scores to pattern weights.

**Implementation Requirements:**
```python
from decimal import Decimal

from src.models.persona_score import PersonaScore
from src.models.pattern_weights import PatternWeights
from src.utils.constants import (
    BETTOR_MODIFIERS,
    FANTASY_MODIFIERS,
    STATS_NERD_MODIFIERS,
)

class WeightMapper:
    """
    Convert persona scores to pattern detection weights.
    
    Why weighted blend:
    - Most users are hybrid personas
    - Proportional weighting = smoother personalization
    - Avoids hard cutoffs
    """
    
    def calculate_weights(self, persona_scores: PersonaScore) -> PatternWeights:
        """
        Generate pattern weights from persona scores.
        
        Formula:
        final_weight = (bettor_score * bettor_modifier) +
                       (fantasy_score * fantasy_modifier) +
                       (stats_score * stats_modifier)
        
        Args:
            persona_scores: User's persona fit scores
            
        Returns:
            PatternWeights with final multipliers
        """
        # Start with base weights (all 1.0)
        base = PatternWeights()
        
        # Apply weighted blend of modifiers
        weights_dict = {}
        for field in base.__dataclass_fields__:
            bettor_mod = BETTOR_MODIFIERS.get(field, Decimal('1.0'))
            fantasy_mod = FANTASY_MODIFIERS.get(field, Decimal('1.0'))
            stats_mod = STATS_NERD_MODIFIERS.get(field, Decimal('1.0'))
            
            final_weight = (
                persona_scores.bettor * bettor_mod +
                persona_scores.fantasy * fantasy_mod +
                persona_scores.stats_nerd * stats_mod
            )
            
            weights_dict[field] = final_weight
        
        return PatternWeights(**weights_dict)
```

**Tests Required:**
- Test pure Bettor (1.0, 0.0, 0.0) produces BETTOR_MODIFIERS
- Test pure Fantasy (0.0, 1.0, 0.0) produces FANTASY_MODIFIERS
- Test pure Stats Nerd (0.0, 0.0, 1.0) produces STATS_NERD_MODIFIERS
- Test hybrid (0.5, 0.3, 0.2) produces blended weights
- Test weight calculation formula

**Acceptance Criteria:**
- [ ] Pure personas match modifier sets exactly
- [ ] Hybrid personas blend proportionally
- [ ] All weights remain positive
- [ ] Formula documented and tested

---

### Phase 3 Checkpoint

**Before proceeding to Phase 4:**
- [ ] Behavioral scorer calculates all metrics correctly
- [ ] Persona detector scores all three personas
- [ ] Weight mapper produces valid weights
- [ ] Integration test: Entry list → Pattern weights

**Integration Test Spec:**
```python
def test_scoring_pipeline_end_to_end():
    """Test complete scoring pipeline"""
    # 1. Parse CSV
    parser = DraftKingsParser()
    entries = parser.parse_csv('fixtures/sample_draftkings.csv')
    
    # 2. Classify contests
    classifier = ContestTypeClassifier()
    for entry in entries:
        entry.contest_type = classifier.classify(entry.contest_name)
    
    # 3. Calculate metrics
    scorer = BehavioralScorer()
    metrics = scorer.calculate_metrics(entries)
    assert metrics.total_entries == len(entries)
    
    # 4. Detect personas
    detector = PersonaDetector()
    personas = detector.score_personas(metrics)
    assert personas.bettor + personas.fantasy + personas.stats_nerd == Decimal('1.0')
    
    # 5. Generate weights
    mapper = WeightMapper()
    weights = mapper.calculate_weights(personas)
    assert all(w > 0 for w in weights.to_dict().values())
```

---

## Phase 4: Storage & Persistence

### Objective
Store user profiles in PostgreSQL for cross-session use.

### Files to Create

#### 4.1 `src/storage/database.py`

**Purpose:** SQLAlchemy database setup and session management.

**Implementation Requirements:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import os

# Database URL from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://localhost/dfs_parser'
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set True for SQL logging in dev
    pool_pre_ping=True,  # Verify connections before use
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for models
Base = declarative_base()

@contextmanager
def get_db_session():
    """
    Provide database session with automatic cleanup.
    
    Usage:
        with get_db_session() as db:
            db.query(UserProfile).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def drop_db():
    """Drop all tables (use with caution)"""
    Base.metadata.drop_all(bind=engine)
```

**Tests Required:**
- Test session context manager
- Test init_db() creates tables
- Test connection pooling

**Acceptance Criteria:**
- [ ] Session management works correctly
- [ ] init_db() creates all tables
- [ ] Connection pool configured properly

---

#### 4.2 `src/models/user_profile.py`

**Purpose:** SQLAlchemy model for user profiles.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from src.storage.database import Base
from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.models.pattern_weights import PatternWeights

class UserProfile(Base):
    """
    User behavioral profile storage.
    
    Why JSON for complex fields:
    - Flexible schema for metrics/weights
    - Avoids 50+ columns
    - Easy to query with PostgreSQL JSON operators
    """
    __tablename__ = 'user_profiles'
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Summary stats
    total_entries_parsed = Column(Integer)
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)
    platforms = Column(JSON)  # ["DRAFTKINGS", "FANDUEL"]
    
    # Behavioral metrics (stored as JSON)
    behavioral_metrics = Column(JSON)
    
    # Persona scores (stored as columns for indexing)
    persona_bettor = Column(DECIMAL(4, 3))
    persona_fantasy = Column(DECIMAL(4, 3))
    persona_stats_nerd = Column(DECIMAL(4, 3))
    
    # Pattern weights (stored as JSON)
    pattern_weights = Column(JSON)
    
    # Metadata
    last_csv_upload = Column(DateTime)
    confidence_score = Column(DECIMAL(4, 3))
    
    def set_behavioral_metrics(self, metrics: BehavioralMetrics):
        """Store BehavioralMetrics as JSON"""
        self.behavioral_metrics = metrics.to_dict()
    
    def get_behavioral_metrics(self) -> BehavioralMetrics:
        """Reconstruct BehavioralMetrics from JSON"""
        if not self.behavioral_metrics:
            return BehavioralMetrics()
        # TODO: Implement from_dict() in BehavioralMetrics
        return BehavioralMetrics(**self.behavioral_metrics)
    
    def set_persona_scores(self, scores: PersonaScore):
        """Store PersonaScore"""
        self.persona_bettor = scores.bettor
        self.persona_fantasy = scores.fantasy
        self.persona_stats_nerd = scores.stats_nerd
    
    def get_persona_scores(self) -> PersonaScore:
        """Reconstruct PersonaScore"""
        return PersonaScore(
            bettor=self.persona_bettor,
            fantasy=self.persona_fantasy,
            stats_nerd=self.persona_stats_nerd,
        )
    
    def set_pattern_weights(self, weights: PatternWeights):
        """Store PatternWeights as JSON"""
        self.pattern_weights = weights.to_dict()
    
    def get_pattern_weights(self) -> PatternWeights:
        """Reconstruct PatternWeights from JSON"""
        return PatternWeights.from_dict(self.pattern_weights)
```

**Tests Required:**
- Test model creation and persistence
- Test JSON serialization/deserialization
- Test timestamp auto-update
- Test UUID generation

**Acceptance Criteria:**
- [ ] Model creates table correctly
- [ ] JSON fields serialize/deserialize properly
- [ ] Timestamps update automatically
- [ ] UUIDs generate uniquely

---

#### 4.3 `src/storage/profile_repository.py`

**Purpose:** CRUD operations for user profiles.

**Implementation Requirements:**
```python
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from src.storage.database import get_db_session
from src.models.user_profile import UserProfile
from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.models.pattern_weights import PatternWeights

class ProfileRepository:
    """
    Repository pattern for UserProfile CRUD.
    
    Why repository:
    - Isolates database logic from business logic
    - Easy to mock for testing
    - Consistent interface for data access
    """
    
    def create_profile(
        self,
        entries_count: int,
        date_range: tuple[datetime, datetime],
        platforms: List[str],
        metrics: BehavioralMetrics,
        personas: PersonaScore,
        weights: PatternWeights,
    ) -> UserProfile:
        """
        Create new user profile.
        
        Returns:
            Saved UserProfile with generated user_id
        """
        with get_db_session() as db:
            profile = UserProfile(
                total_entries_parsed=entries_count,
                date_range_start=date_range[0],
                date_range_end=date_range[1],
                platforms=platforms,
                last_csv_upload=datetime.utcnow(),
                confidence_score=metrics.confidence_score,
            )
            
            profile.set_behavioral_metrics(metrics)
            profile.set_persona_scores(personas)
            profile.set_pattern_weights(weights)
            
            db.add(profile)
            db.flush()  # Get user_id before commit
            db.refresh(profile)
            
            return profile
    
    def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Retrieve profile by ID"""
        with get_db_session() as db:
            return db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
    
    def update_profile(
        self,
        user_id: UUID,
        metrics: BehavioralMetrics,
        personas: PersonaScore,
        weights: PatternWeights,
    ) -> UserProfile:
        """Update existing profile with new data"""
        with get_db_session() as db:
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                raise ValueError(f"Profile not found: {user_id}")
            
            profile.set_behavioral_metrics(metrics)
            profile.set_persona_scores(personas)
            profile.set_pattern_weights(weights)
            profile.last_csv_upload = datetime.utcnow()
            profile.confidence_score = metrics.confidence_score
            
            db.flush()
            db.refresh(profile)
            
            return profile
    
    def delete_profile(self, user_id: UUID) -> bool:
        """Delete profile (privacy/GDPR)"""
        with get_db_session() as db:
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                return False
            
            db.delete(profile)
            return True
    
    def list_profiles(self, limit: int = 100) -> List[UserProfile]:
        """List all profiles (admin function)"""
        with get_db_session() as db:
            return db.query(UserProfile).limit(limit).all()
```

**Tests Required:**
- Test create_profile()
- Test get_profile()
- Test update_profile()
- Test delete_profile()
- Test list_profiles()
- Test get nonexistent profile returns None

**Acceptance Criteria:**
- [ ] All CRUD operations work
- [ ] Returns None for missing profiles
- [ ] Raises error on update of nonexistent profile
- [ ] Delete returns boolean correctly

---

### Phase 4 Checkpoint

**Before proceeding to Phase 5:**
- [ ] Database schema created
- [ ] Repository operations tested
- [ ] Profile persistence works end-to-end
- [ ] JSON serialization/deserialization works

**Integration Test Spec:**
```python
def test_profile_persistence_end_to_end():
    """Test complete persistence pipeline"""
    # 1. Parse and score (reuse from Phase 3)
    parser = DraftKingsParser()
    entries = parser.parse_csv('fixtures/sample_draftkings.csv')
    
    classifier = ContestTypeClassifier()
    for entry in entries:
        entry.contest_type = classifier.classify(entry.contest_name)
    
    scorer = BehavioralScorer()
    metrics = scorer.calculate_metrics(entries)
    
    detector = PersonaDetector()
    personas = detector.score_personas(metrics)
    
    mapper = WeightMapper()
    weights = mapper.calculate_weights(personas)
    
    # 2. Save to database
    repo = ProfileRepository()
    dates = [e.date for e in entries]
    date_range = (min(dates), max(dates))
    platforms = list(set(e.source for e in entries))
    
    profile = repo.create_profile(
        entries_count=len(entries),
        date_range=date_range,
        platforms=platforms,
        metrics=metrics,
        personas=personas,
        weights=weights,
    )
    
    # 3. Retrieve and verify
    retrieved = repo.get_profile(profile.user_id)
    assert retrieved is not None
    assert retrieved.total_entries_parsed == len(entries)
    
    retrieved_personas = retrieved.get_persona_scores()
    assert retrieved_personas.bettor == personas.bettor
```

---

## Phase 5: Test Data & Sample CSVs

### Objective
Create realistic test fixtures for all testing scenarios.

### Files to Create

#### 5.1 `tests/fixtures/sample_draftkings.csv`

**Content:**
```csv
Entry ID,Contest Name,Contest ID,Entry Fee,Winnings,Sport,Date Entered,Points
12345,NFL $20K Shot,98765,$3.00,$5.50,NFL,2024-09-15 13:00:00,156.42
12346,NFL Sunday Million [$1M GTD],98766,$20.00,$0.00,NFL,2024-09-15 13:00:00,142.18
12347,NBA 50/50,98767,$5.00,$9.50,NBA,2024-10-22 19:00:00,198.65
12348,NHL Head to Head,98768,$2.00,$3.80,NHL,2024-10-15 19:00:00,87.23
12349,NBA 3-Max,98769,$10.00,$28.00,NBA,2024-10-23 19:00:00,223.45
12350,NFL Millionaire Maker,98770,$15.00,$0.00,NFL,2024-09-22 13:00:00,134.76
12351,NBA Double Up,98771,$10.00,$19.00,NBA,2024-10-24 19:00:00,201.34
12352,Free NFL Contest,98772,$0.00,$0.00,NFL,2024-09-08 13:00:00,98.12
```

**Purpose:** Standard DK format with variety of contest types, sports, stakes.

---

#### 5.2 `tests/fixtures/sample_fanduel.csv`

**Content:**
```csv
Entry ID,Contest,Entry Fee,Winnings,Points,Sport,Entered
67890,NFL Sunday Million [$1M GTD],$5.00,$0.00,142.5,NFL,"Sep 15, 2024 1:00PM"
67891,NBA 50/50,$10.00,$19.00,198.2,NBA,"Oct 22, 2024 7:00PM"
67892,NHL Head to Head,$3.00,$5.70,87.8,NHL,"Oct 15, 2024 7:00PM"
67893,NBA Multiplier,$15.00,$0.00,156.3,NBA,"Oct 23, 2024 7:00PM"
67894,NFL Playoff Challenge,$20.00,$45.00,234.6,NFL,"Sep 22, 2024 1:00PM"
```

**Purpose:** Standard FD format with date format variations.

---

#### 5.3 `tests/fixtures/sample_edge_cases.csv`

**Content:** DK format with edge cases
```csv
Entry ID,Contest Name,Contest ID,Entry Fee,Winnings,Sport,Date Entered,Points
99991,Unknown Contest Type,11111,$5.00,$10.00,NFL,2024-09-15 13:00:00,150.00
99992,Very High Stakes Contest,11112,$500.00,$0.00,NBA,2024-10-22 19:00:00,145.23
99993,Fractional Winnings,11113,$3.00,$3.47,NHL,2024-10-15 19:00:00,88.91
99994,Zero Points,11114,$5.00,$0.00,MLB,2024-08-20 19:00:00,0.00
99995,Old Data,11115,$2.00,$4.00,NFL,2020-09-15 13:00:00,120.45
```

**Purpose:** Test edge cases (unknown contest, high stakes, old data, etc.)

---

#### 5.4 `scripts/sample_data_generator.py`

**Purpose:** Generate larger synthetic datasets for performance testing.

**Implementation:**
```python
import csv
import random
from datetime import datetime, timedelta
from decimal import Decimal

def generate_draftkings_csv(num_entries: int, filepath: str):
    """Generate synthetic DK CSV for testing"""
    
    sports = ['NFL', 'NBA', 'NHL', 'MLB', 'PGA']
    contest_types = [
        'Sunday Million [$1M GTD]',
        '50/50',
        'Head to Head',
        '3-Max',
        'Millionaire Maker',
        'Double Up',
    ]
    
    start_date = datetime(2024, 1, 1)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Entry ID', 'Contest Name', 'Contest ID',
            'Entry Fee', 'Winnings', 'Sport', 'Date Entered', 'Points'
        ])
        
        for i in range(num_entries):
            entry_id = 10000 + i
            sport = random.choice(sports)
            contest = random.choice(contest_types)
            contest_name = f"{sport} {contest}"
            contest_id = 90000 + i
            entry_fee = random.choice([2, 3, 5, 10, 20, 50])
            
            # 30% win rate
            if random.random() < 0.3:
                winnings = entry_fee * random.uniform(1.5, 3.0)
            else:
                winnings = 0.0
            
            days_ago = random.randint(0, 365)
            date = start_date + timedelta(days=days_ago)
            points = random.uniform(80, 250)
            
            writer.writerow([
                entry_id, contest_name, contest_id,
                f"${entry_fee:.2f}", f"${winnings:.2f}",
                sport, date.strftime('%Y-%m-%d %H:%M:%S'),
                f"{points:.2f}"
            ])

if __name__ == '__main__':
    generate_draftkings_csv(1000, 'tests/fixtures/large_dk_dataset.csv')
    print("Generated 1000-entry test dataset")
```

---

### Phase 5 Checkpoint

**Test data requirements:**
- [ ] Sample CSVs for both platforms
- [ ] Edge case CSV with corner cases
- [ ] Large dataset generator for performance testing
- [ ] All fixtures committed to repo

---

## Phase 6: CLI & Integration

### Objective
Command-line interface for testing and demo purposes.

### Files to Create

#### 6.1 `scripts/init_db.py`

**Purpose:** Initialize database schema.

**Implementation:**
```python
from src.storage.database import init_db, drop_db
import sys

def main():
    """Initialize or reset database"""
    
    if '--reset' in sys.argv:
        confirm = input("This will DELETE all data. Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            print("Dropping existing tables...")
            drop_db()
        else:
            print("Aborted.")
            return
    
    print("Creating database tables...")
    init_db()
    print("Database initialized successfully!")

if __name__ == '__main__':
    main()
```

---

#### 6.2 `src/cli.py`

**Purpose:** Command-line interface for end-to-end pipeline.

**Implementation:**
```python
import argparse
from pathlib import Path

from src.parsers.platform_detector import PlatformDetector
from src.parsers.draftkings_parser import DraftKingsParser
from src.parsers.fanduel_parser import FanDuelParser
from src.classifiers.contest_type_classifier import ContestTypeClassifier
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.persona_detector import PersonaDetector
from src.scoring.weight_mapper import WeightMapper
from src.storage.profile_repository import ProfileRepository
from src.utils.constants import PLATFORM_DRAFTKINGS, PLATFORM_FANDUEL

def main():
    parser = argparse.ArgumentParser(
        description='DFS Behavioral Parser - Persona Detection'
    )
    parser.add_argument(
        'csv_files',
        nargs='+',
        help='CSV file(s) to parse'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save profile to database'
    )
    parser.add_argument(
        '--user-id',
        help='User ID for update (if saving)'
    )
    
    args = parser.parse_args()
    
    # 1. Parse all CSV files
    all_entries = []
    platforms_used = set()
    
    for csv_file in args.csv_files:
        print(f"\nParsing {csv_file}...")
        
        # Detect platform
        with open(csv_file) as f:
            columns = f.readline().strip().split(',')
        
        detector = PlatformDetector()
        platform = detector.detect(columns)
        platforms_used.add(platform)
        print(f"Detected platform: {platform}")
        
        # Parse with appropriate parser
        if platform == PLATFORM_DRAFTKINGS:
            parser_obj = DraftKingsParser()
        else:
            parser_obj = FanDuelParser()
        
        entries = parser_obj.parse_csv(csv_file)
        print(f"Parsed {len(entries)} entries")
        
        # Classify contests
        classifier = ContestTypeClassifier()
        for entry in entries:
            entry.contest_type = classifier.classify(entry.contest_name)
        
        all_entries.extend(entries)
    
    print(f"\n=== Total: {len(all_entries)} entries from {len(platforms_used)} platform(s) ===\n")
    
    # 2. Calculate metrics
    print("Calculating behavioral metrics...")
    scorer = BehavioralScorer()
    metrics = scorer.calculate_metrics(all_entries)
    
    print(f"  Total invested: ${metrics.total_invested}")
    print(f"  Total winnings: ${metrics.total_winnings}")
    print(f"  ROI: {metrics.roi_overall:.2f}%")
    print(f"  GPP%: {metrics.gpp_percentage:.1%}")
    print(f"  Cash%: {metrics.cash_percentage:.1%}")
    print(f"  Sport diversity: {metrics.sport_diversity:.2f}")
    
    # 3. Detect personas
    print("\nDetecting personas...")
    detector = PersonaDetector()
    personas = detector.score_personas(metrics)
    
    print(f"  Bettor: {personas.bettor:.1%}")
    print(f"  Fantasy: {personas.fantasy:.1%}")
    print(f"  Stats Nerd: {personas.stats_nerd:.1%}")
    print(f"  Primary: {personas.primary_persona}")
    print(f"  Hybrid: {personas.is_hybrid}")
    print(f"  Confidence: {personas.confidence:.2f}")
    
    # 4. Generate weights
    print("\nGenerating pattern weights...")
    mapper = WeightMapper()
    weights = mapper.calculate_weights(personas)
    
    for name, value in weights.to_dict().items():
        print(f"  {name}: {value}")
    
    # 5. Save if requested
    if args.save:
        print("\nSaving profile to database...")
        repo = ProfileRepository()
        
        dates = [e.date for e in all_entries]
        date_range = (min(dates), max(dates))
        
        if args.user_id:
            # Update existing
            from uuid import UUID
            profile = repo.update_profile(
                user_id=UUID(args.user_id),
                metrics=metrics,
                personas=personas,
                weights=weights,
            )
            print(f"Updated profile: {profile.user_id}")
        else:
            # Create new
            profile = repo.create_profile(
                entries_count=len(all_entries),
                date_range=date_range,
                platforms=list(platforms_used),
                metrics=metrics,
                personas=personas,
                weights=weights,
            )
            print(f"Created profile: {profile.user_id}")
            print("Save this ID for future updates!")

if __name__ == '__main__':
    main()
```

---

### Phase 6 Checkpoint

**CLI requirements:**
- [ ] Can parse single or multiple CSVs
- [ ] Displays all metrics and persona scores
- [ ] Can save to database
- [ ] Can update existing profiles
- [ ] Clear error messages on failure

---

## Deployment Checklist

**Before shipping to production:**

### Code Quality
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Test coverage > 80%
- [ ] No TODO comments in production code
- [ ] All docstrings complete
- [ ] Type hints on all functions

### Performance
- [ ] CSV parsing < 500ms for 10K entries
- [ ] Persona scoring < 100ms
- [ ] Database queries optimized
- [ ] Tested with large datasets (100K+ entries)

### Security
- [ ] Database credentials in environment variables
- [ ] No hardcoded secrets
- [ ] SQL injection prevention (using ORM)
- [ ] Input validation on all user data

### Documentation
- [ ] README with setup instructions
- [ ] API documentation (if exposing)
- [ ] Example usage
- [ ] Troubleshooting guide

### Database
- [ ] Migration scripts
- [ ] Backup strategy
- [ ] Index optimization
- [ ] Connection pooling configured

---

## Future Enhancements (Post-MVP)

### Phase 7: Profile Evolution Tracking
- Store historical persona scores
- Detect persona drift over time
- Alert on significant changes

### Phase 8: Recommendations Engine
- Contest recommendations based on persona
- "Users like you also play..."
- Expected value suggestions

### Phase 9: Browser Extension
- Auto-download CSVs from DK/FD
- One-click profile updates
- Real-time persona tracking

### Phase 10: Multi-User Analytics
- Aggregate anonymized insights
- Benchmarking vs peer group
- "Top 15% ROI for Fantasy players"

---

## Error Handling Standards

**All modules must:**
1. Use specific exceptions (ValueError, KeyError, etc.)
2. Provide clear error messages with context
3. Log warnings for recoverable errors
4. Fail fast on unrecoverable errors
5. Never silently swallow exceptions

**Example:**
```python
# BAD
try:
    value = some_dict[key]
except:
    pass

# GOOD
try:
    value = some_dict[key]
except KeyError as e:
    raise ValueError(f"Required configuration missing: {key}") from e
```

---

## Logging Standards

**Use Python logging module:**
```python
import logging

logger = logging.getLogger(__name__)

# Levels:
logger.debug("CSV parsing started")      # Verbose debugging
logger.info("Parsed 1234 entries")       # Normal operation
logger.warning("Skipped malformed row")  # Recoverable issue
logger.error("Database connection failed") # Error but continuing
logger.critical("Data corruption detected") # Fatal error
```

---

## Code Style

**Follow:**
- PEP 8 for Python style
- Black for formatting (line length 88)
- isort for import ordering
- Type hints everywhere
- Docstrings in Google style

**Pre-commit hooks:**
```bash
pip install pre-commit black isort flake8
pre-commit install
```

---

## Testing Philosophy

**Unit Tests:**
- Test one function at a time
- Mock external dependencies
- Fast (< 1s per test)
- Deterministic (no random data)

**Integration Tests:**
- Test multiple components together
- Use real database (test instance)
- Use fixture data
- Can be slower

**Test Naming:**
```python
def test_<function>_<scenario>_<expected_result>():
    # Example:
    def test_parse_csv_with_missing_columns_raises_error():
        ...
```

---

## Final Notes for Claude Code

**Build Order:**
1. Phase 1 first - foundational models
2. Run tests after each file
3. Don't proceed to next phase until all tests pass
4. If uncertain about implementation, ask for clarification
5. Commit after each successful phase

**When stuck:**
- Check constants.py for configuration
- Review similar code in base classes
- Run existing tests to see patterns
- Ask specific questions with context

**Success criteria:**
- Can parse 10K entry CSV in < 500ms
- Persona detection feels "right" to manual review
- Database persistence works reliably
- CLI provides clear, actionable output

---

## Environment Setup

**Create `.env.example`:**
```bash
DATABASE_URL=postgresql://localhost/dfs_parser
LOG_LEVEL=INFO
```

**Requirements.txt:**
```
pandas>=2.0.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
python-dateutil>=2.8.0
pytest>=7.0.0
pytest-cov>=4.0.0
```

---

**Ready to build? Start with Phase 1 and work systematically through each phase. Good luck!**
