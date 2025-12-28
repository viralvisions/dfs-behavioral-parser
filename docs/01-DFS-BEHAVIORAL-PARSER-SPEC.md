# DFS Behavioral Parser - Complete Technical Specification

## Project Overview
Build CSV parser that ingests DraftKings/FanDuel transaction history to auto-detect user personas (Bettor/Fantasy Player/Stats Nerd) and generate weighted pattern detection coefficients for ThirdDownIQ, ShotClockIQ, and PowerPlayIQ apps.

**Business Goal:** Personalization without friction - user uploads CSVs once, system auto-configures analytics weights across all sports apps.

**Revenue Impact:** 99%+ margins via autonomous personalization vs manual configuration.

---

## Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI (API endpoints)
- **Database:** PostgreSQL (profile persistence)
- **Testing:** pytest, pytest-cov, pytest-benchmark
- **Money:** Python Decimal (NEVER float)
- **Validation:** pydantic v2
- **Deployment:** Railway (microservice)

---

## Architecture

```
┌─────────────────────────────────────────┐
│         DFS Behavioral Parser           │
│         (Microservice API)              │
│      https://parser-api.railway.app     │
└─────────────────────────────────────────┘
                    ▲
                    │ API calls
        ┌───────────┼───────────┐
        │           │           │
┌───────────┐ ┌───────────┐ ┌───────────┐
│ThirdDownIQ│ │ShotClockIQ│ │PowerPlayIQ│
│   (NFL)   │ │   (NBA)   │ │   (NHL)   │
└───────────┘ └───────────┘ └───────────┘
```

**Flow:**
1. User uploads DK/FD CSV to any sport app
2. App sends CSV to Parser API
3. Parser returns: `PersonaScore` + `PatternWeights`
4. App applies weights to pattern detection
5. User sees personalized insights

---

## Phase 1: Data Models & Validation

**Goal:** Define core data structures with strict validation

### 1.1 DFSEntry Model
**File:** `src/models/dfs_entry.py`

```python
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class DFSEntry(BaseModel):
    """
    Normalized DFS contest entry from DraftKings or FanDuel.
    Why: Single data structure for both platforms enables unified analysis.
    """
    entry_id: str
    date: datetime
    sport: str  # Uppercase: NFL, NBA, NHL, MLB, etc.
    contest_type: Literal["GPP", "CASH", "H2H", "MULTI", "UNKNOWN"]
    entry_fee: Decimal = Field(ge=0)  # Must be non-negative
    winnings: Decimal = Field(ge=0)
    points: Decimal
    source: Literal["DK", "FD"]
    
    @field_validator('entry_fee', 'winnings')
    @classmethod
    def validate_money(cls, v):
        """Ensure Decimal precision for money"""
        if not isinstance(v, Decimal):
            raise ValueError("Money fields must be Decimal type")
        return v
    
    @property
    def roi(self) -> Decimal:
        """Return on investment percentage"""
        if self.entry_fee == 0:
            return Decimal('0')
        return ((self.winnings - self.entry_fee) / self.entry_fee) * 100
    
    @property
    def profit(self) -> Decimal:
        """Net profit/loss"""
        return self.winnings - self.entry_fee
    
    @property
    def is_profitable(self) -> bool:
        """Did this entry win money?"""
        return self.profit > 0
```

**Acceptance Criteria:**
- ✅ All money fields use Decimal (NEVER float - prevents rounding errors)
- ✅ Date parsing handles both DK and FD formats
- ✅ ROI calculation: `((winnings - entry_fee) / entry_fee) * 100`
- ✅ Handles zero entry_fee without division error
- ✅ Validation rejects negative fees/winnings
- ✅ Type hints on all functions (mypy --strict passes)

**Test Coverage:** >95%

---

### 1.2 BehavioralMetrics Model
**File:** `src/models/behavioral_metrics.py`

```python
from decimal import Decimal
from pydantic import BaseModel
from typing import Dict

class BehavioralMetrics(BaseModel):
    """
    Aggregated metrics from entry history.
    Why: Single source of truth for persona detection.
    """
    # Volume metrics
    total_entries: int
    entries_by_sport: Dict[str, int]
    entries_by_contest_type: Dict[str, int]
    
    # Financial metrics
    total_invested: Decimal
    total_winnings: Decimal
    avg_entry_fee: Decimal
    roi_overall: Decimal
    
    # Behavior patterns
    gpp_percentage: Decimal  # 0.0 to 1.0
    cash_percentage: Decimal
    multi_entry_rate: Decimal  # Avg entries per contest
    sport_diversity: Decimal  # Shannon entropy
    stake_variance: Decimal  # Coefficient of variation
    
    # Temporal patterns
    entries_per_week: Decimal
    most_active_day: str  # "Monday", "Tuesday", etc.
    recency_score: Decimal  # 0.0 to 1.0, higher = more recent
```

**Acceptance Criteria:**
- ✅ All percentages stored as Decimal 0.0-1.0
- ✅ sport_diversity uses Shannon entropy
- ✅ stake_variance is coefficient of variation
- ✅ recency_score weights recent entries exponentially

**Test Coverage:** >90%

---

### 1.3 PersonaScore Model
**File:** `src/models/persona_score.py`

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator

class PersonaScore(BaseModel):
    """
    Confidence scores for each persona archetype.
    Why: Users often hybrid, need weighted blend not binary classification.
    """
    bettor: Decimal  # 0.0 to 1.0
    fantasy: Decimal
    stats_nerd: Decimal
    
    @field_validator('bettor', 'fantasy', 'stats_nerd')
    @classmethod
    def validate_score(cls, v):
        """Scores must be 0.0-1.0"""
        if not (0 <= v <= 1):
            raise ValueError("Scores must be between 0.0 and 1.0")
        return v
    
    @property
    def primary_persona(self) -> str:
        """Return highest scoring persona"""
        scores = {
            'bettor': self.bettor,
            'fantasy': self.fantasy,
            'stats_nerd': self.stats_nerd
        }
        return max(scores, key=scores.get)
    
    @property
    def is_hybrid(self) -> bool:
        """True if multiple personas > 0.3"""
        scores = [self.bettor, self.fantasy, self.stats_nerd]
        return sum(1 for s in scores if s > Decimal('0.3')) >= 2
    
    @property
    def confidence(self) -> Decimal:
        """Highest score value"""
        return max(self.bettor, self.fantasy, self.stats_nerd)
```

**Acceptance Criteria:**
- ✅ Scores sum to ~1.0 (normalized)
- ✅ primary_persona returns correct string
- ✅ is_hybrid logic correct
- ✅ Handles edge case where all scores equal

**Test Coverage:** >95%

---

### 1.4 PatternWeights Model
**File:** `src/models/pattern_weights.py`

```python
from decimal import Decimal
from pydantic import BaseModel, Field

class PatternWeights(BaseModel):
    """
    Multipliers for pattern detection algorithms.
    Why: Bettor cares about line movement, Stats Nerd wants correlations.
    """
    line_movement: Decimal = Field(default=Decimal('1.0'), ge=0)
    historical_trends: Decimal = Field(default=Decimal('1.0'), ge=0)
    injury_impact: Decimal = Field(default=Decimal('1.0'), ge=0)
    weather_factors: Decimal = Field(default=Decimal('1.0'), ge=0)
    player_correlations: Decimal = Field(default=Decimal('1.0'), ge=0)
    situational_stats: Decimal = Field(default=Decimal('1.0'), ge=0)
    live_odds_delta: Decimal = Field(default=Decimal('1.0'), ge=0)
    contrarian_plays: Decimal = Field(default=Decimal('1.0'), ge=0)
    
    def apply_to_pattern(self, pattern_value: Decimal, weight_key: str) -> Decimal:
        """Apply weight to a pattern value"""
        weight = getattr(self, weight_key, Decimal('1.0'))
        return pattern_value * weight
```

**Acceptance Criteria:**
- ✅ Default weights all = 1.0
- ✅ apply_to_pattern multiplies correctly
- ✅ Validation rejects negative weights
- ✅ Serializes to JSON cleanly

**Test Coverage:** >90%

---

### 1.5 UserProfile Model
**File:** `src/models/user_profile.py`

```python
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List
from .behavioral_metrics import BehavioralMetrics
from .persona_score import PersonaScore
from .pattern_weights import PatternWeights

class UserProfile(BaseModel):
    """
    Complete user behavioral profile.
    Why: Persist persona for cross-session, cross-app use.
    """
    user_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Source data summary
    total_entries_parsed: int
    date_range_start: datetime
    date_range_end: datetime
    platforms: List[str]  # ["DK", "FD"]
    
    # Computed metrics
    behavioral_metrics: BehavioralMetrics
    persona_scores: PersonaScore
    pattern_weights: PatternWeights
    
    # Metadata
    last_csv_upload: datetime
    confidence_score: Decimal  # 0.0-1.0, data quality indicator
```

**Acceptance Criteria:**
- ✅ UUID for user_id
- ✅ Timestamps auto-populate
- ✅ Nested models validate
- ✅ Serializes to JSON cleanly

**Test Coverage:** >90%

---

## Phase 2: CSV Parsing & Classification

**Goal:** Ingest and normalize DK/FD CSVs

### 2.1 Contest Classifier
**File:** `src/parsers/contest_classifier.py`

```python
import re
from typing import Literal

ContestType = Literal["GPP", "CASH", "H2H", "MULTI", "UNKNOWN"]

class ContestTypeClassifier:
    """
    Extract contest type from name using pattern matching.
    Why: Names inconsistent across platforms, need reliable categorization.
    """
    
    GPP_PATTERNS = [
        r'\$[\d,]+',           # "$20K"
        r'milly|million',      # "Sunday Million"
        r'shot|sharpshooter',  # "Millionaire Maker Shot"
        r'gtd|guaranteed',     # "$10K GTD"
        r'maker',              # "Millionaire Maker"
    ]
    
    CASH_PATTERNS = [
        r'double.?up',         # "Double Up"
        r'50/50',
        r'cash',
    ]
    
    H2H_PATTERNS = [
        r'head.?to.?head|h2h',
    ]
    
    MULTI_PATTERNS = [
        r'\d+-max',            # "3-max", "5-max"
        r'multiplier',
    ]
    
    def classify(self, contest_name: str) -> ContestType:
        """
        Classify contest type from name.
        Priority: CASH > H2H > MULTI > GPP (most specific first)
        """
        name_lower = contest_name.lower()
        
        # Check CASH first (most specific)
        for pattern in self.CASH_PATTERNS:
            if re.search(pattern, name_lower):
                return "CASH"
        
        # Check H2H
        for pattern in self.H2H_PATTERNS:
            if re.search(pattern, name_lower):
                return "H2H"
        
        # Check MULTI
        for pattern in self.MULTI_PATTERNS:
            if re.search(pattern, name_lower):
                return "MULTI"
        
        # Check GPP
        for pattern in self.GPP_PATTERNS:
            if re.search(pattern, name_lower):
                return "GPP"
        
        return "UNKNOWN"
```

**Acceptance Criteria:**
- ✅ classify("NFL $20K Shot") returns "GPP"
- ✅ classify("50/50") returns "CASH"
- ✅ classify("3-max") returns "MULTI"
- ✅ classify("Random Contest") returns "UNKNOWN"
- ✅ Case-insensitive matching
- ✅ Priority order respected

**Test Coverage:** >95% with 20+ real contest names

---

### 2.2 CSV Validator
**File:** `src/utils/csv_validator.py`

```python
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
        "Entry ID", "Contest", "Entry Fee", 
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
```

**Acceptance Criteria:**
- ✅ detect_platform() returns correct platform
- ✅ validate_size() raises error for files >10MB
- ✅ validate_extension() only accepts .csv
- ✅ Handles BOM markers

**Test Coverage:** >90%

---

### 2.3 DFS History Parser
**File:** `src/parsers/dfs_history_parser.py`

```python
import csv
from decimal import Decimal
from datetime import datetime
from typing import List
from io import StringIO
from .contest_classifier import ContestTypeClassifier
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
    
    def parse_csv_string(self, csv_content: str) -> List[DFSEntry]:
        """Main entry point for CSV parsing"""
        # Validate
        self.validator.validate_size(csv_content)
        
        # Detect platform
        platform = self.validator.detect_platform(csv_content)
        
        if platform == "DRAFTKINGS":
            return self._parse_draftkings(csv_content)
        elif platform == "FANDUEL":
            return self._parse_fanduel(csv_content)
        else:
            raise ValueError("Unknown CSV format - must be DraftKings or FanDuel")
    
    def _parse_draftkings(self, csv_content: str) -> List[DFSEntry]:
        """Parse DraftKings CSV format"""
        entries = []
        reader = csv.DictReader(StringIO(csv_content))
        
        for row in reader:
            try:
                entry = DFSEntry(
                    entry_id=row["Entry ID"],
                    date=self._parse_dk_date(row["Date Entered"]),
                    sport=row["Sport"].upper(),
                    contest_type=self.classifier.classify(row["Contest Name"]),
                    entry_fee=self._parse_money(row["Entry Fee"]),
                    winnings=self._parse_money(row["Winnings"]),
                    points=Decimal(row.get("Points", "0")),
                    source="DK"
                )
                entries.append(entry)
            except Exception as e:
                # Log warning but continue
                print(f"Warning: Skipping malformed row: {e}")
                continue
        
        return entries
    
    def _parse_fanduel(self, csv_content: str) -> List[DFSEntry]:
        """Parse FanDuel CSV format"""
        entries = []
        reader = csv.DictReader(StringIO(csv_content))
        
        for row in reader:
            try:
                entry = DFSEntry(
                    entry_id=row["Entry ID"],
                    date=self._parse_fd_date(row["Entered"]),
                    sport=row["Sport"].upper(),
                    contest_type=self.classifier.classify(row["Contest"]),
                    entry_fee=self._parse_money(row["Entry Fee"]),
                    winnings=self._parse_money(row["Winnings"]),
                    points=Decimal(row.get("Points", "0")),
                    source="FD"
                )
                entries.append(entry)
            except Exception as e:
                print(f"Warning: Skipping malformed row: {e}")
                continue
        
        return entries
    
    def _parse_money(self, value: str) -> Decimal:
        """Strip $ and convert to Decimal"""
        clean = value.replace("$", "").replace(",", "").strip()
        return Decimal(clean) if clean else Decimal("0")
    
    def _parse_dk_date(self, date_str: str) -> datetime:
        """Parse DK format: '2024-09-15 13:00:00'"""
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    
    def _parse_fd_date(self, date_str: str) -> datetime:
        """Parse FD format: 'Sep 17, 2024 1:00PM'"""
        return datetime.strptime(date_str, "%b %d, %Y %I:%M%p")
```

**Acceptance Criteria:**
- ✅ Parses DK CSV correctly
- ✅ Parses FD CSV correctly
- ✅ Skips malformed rows (logs warning)
- ✅ Handles free entries (entry_fee=0)
- ✅ Strips "$" from money fields
- ✅ Performance: <500ms for 10K entries

**Test Coverage:** >90% with real sample CSVs

---

## Phase 3: Behavioral Scoring

**Goal:** Transform entries into behavioral metrics

### 3.1 Behavioral Scorer
**File:** `src/scoring/behavioral_scorer.py`

```python
from decimal import Decimal
from typing import List, Dict
from collections import Counter
import math
from ..models.dfs_entry import DFSEntry
from ..models.behavioral_metrics import BehavioralMetrics

class BehavioralScorer:
    """
    Calculate behavioral metrics from parsed entries.
    Why: Transform raw data into actionable persona signals.
    """
    
    def calculate_metrics(self, entries: List[DFSEntry]) -> BehavioralMetrics:
        """Main entry point for metrics calculation"""
        
        return BehavioralMetrics(
            total_entries=len(entries),
            entries_by_sport=self._count_by_sport(entries),
            entries_by_contest_type=self._count_by_contest_type(entries),
            total_invested=sum(e.entry_fee for e in entries),
            total_winnings=sum(e.winnings for e in entries),
            avg_entry_fee=self._calculate_avg_fee(entries),
            roi_overall=self._calculate_overall_roi(entries),
            gpp_percentage=self._calculate_gpp_percentage(entries),
            cash_percentage=self._calculate_cash_percentage(entries),
            multi_entry_rate=self._calculate_multi_entry_rate(entries),
            sport_diversity=self._calculate_sport_diversity(entries),
            stake_variance=self._calculate_stake_variance(entries),
            entries_per_week=self._calculate_entries_per_week(entries),
            most_active_day=self._find_most_active_day(entries),
            recency_score=self._calculate_recency_score(entries)
        )
    
    def _count_by_sport(self, entries: List[DFSEntry]) -> Dict[str, int]:
        """Count entries by sport"""
        return dict(Counter(e.sport for e in entries))
    
    def _count_by_contest_type(self, entries: List[DFSEntry]) -> Dict[str, int]:
        """Count entries by contest type"""
        return dict(Counter(e.contest_type for e in entries))
    
    def _calculate_avg_fee(self, entries: List[DFSEntry]) -> Decimal:
        """Average entry fee"""
        if not entries:
            return Decimal('0')
        return sum(e.entry_fee for e in entries) / len(entries)
    
    def _calculate_overall_roi(self, entries: List[DFSEntry]) -> Decimal:
        """Overall ROI percentage"""
        total_invested = sum(e.entry_fee for e in entries)
        if total_invested == 0:
            return Decimal('0')
        total_profit = sum(e.profit for e in entries)
        return (total_profit / total_invested) * 100
    
    def _calculate_gpp_percentage(self, entries: List[DFSEntry]) -> Decimal:
        """Percentage of entries in GPP contests"""
        if not entries:
            return Decimal('0')
        gpp_count = sum(1 for e in entries if e.contest_type == "GPP")
        return Decimal(gpp_count) / Decimal(len(entries))
    
    def _calculate_cash_percentage(self, entries: List[DFSEntry]) -> Decimal:
        """Percentage of entries in cash games"""
        if not entries:
            return Decimal('0')
        cash_count = sum(1 for e in entries if e.contest_type in ["CASH", "H2H"])
        return Decimal(cash_count) / Decimal(len(entries))
    
    def _calculate_multi_entry_rate(self, entries: List[DFSEntry]) -> Decimal:
        """Average entries per unique contest"""
        # Group by contest name (approximation)
        # In real implementation, would need contest_id
        return Decimal('1.0')  # Placeholder
    
    def _calculate_sport_diversity(self, entries: List[DFSEntry]) -> Decimal:
        """Shannon entropy of sport distribution (0=focused, 1=diverse)"""
        if not entries:
            return Decimal('0')
        
        sport_counts = Counter(e.sport for e in entries)
        total = len(entries)
        
        entropy = 0.0
        for count in sport_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        # Normalize to 0-1 range (assuming max 4 sports)
        max_entropy = math.log2(4)
        return Decimal(str(min(entropy / max_entropy, 1.0)))
    
    def _calculate_stake_variance(self, entries: List[DFSEntry]) -> Decimal:
        """Coefficient of variation in entry fees"""
        if len(entries) < 2:
            return Decimal('0')
        
        fees = [float(e.entry_fee) for e in entries]
        mean = sum(fees) / len(fees)
        variance = sum((x - mean) ** 2 for x in fees) / len(fees)
        std_dev = math.sqrt(variance)
        
        if mean == 0:
            return Decimal('0')
        return Decimal(str(std_dev / mean))
    
    def _calculate_entries_per_week(self, entries: List[DFSEntry]) -> Decimal:
        """Average entries per week"""
        if not entries:
            return Decimal('0')
        
        dates = [e.date for e in entries]
        date_range = (max(dates) - min(dates)).days
        weeks = max(date_range / 7, 1)
        
        return Decimal(len(entries)) / Decimal(str(weeks))
    
    def _find_most_active_day(self, entries: List[DFSEntry]) -> str:
        """Most common day of week for entries"""
        if not entries:
            return "Unknown"
        
        days = Counter(e.date.strftime("%A") for e in entries)
        return days.most_common(1)[0][0]
    
    def _calculate_recency_score(self, entries: List[DFSEntry]) -> Decimal:
        """Exponential decay weighting recent entries higher"""
        if not entries:
            return Decimal('0')
        
        # Placeholder: could implement exponential decay
        return Decimal('1.0')
```

**Acceptance Criteria:**
- ✅ All metrics calculate correctly
- ✅ Shannon entropy for diversity
- ✅ Coefficient of variation for variance
- ✅ Performance: <100ms for 1K entries

**Test Coverage:** >90%

---

## Phase 4: Persona Detection

**Goal:** Map metrics to persona scores

### 4.1 Persona Detector
**File:** `src/scoring/persona_detector.py`

```python
from decimal import Decimal
from typing import Tuple
from ..models.behavioral_metrics import BehavioralMetrics
from ..models.persona_score import PersonaScore

class PersonaDetector:
    """
    Score user against persona archetypes.
    Why: Auto-select pattern weights without user friction.
    """
    
    # Signal ranges: (min, max) for each metric
    BETTOR_SIGNALS = {
        'gpp_percentage': (Decimal('0.7'), Decimal('1.0')),
        'avg_entry_fee': (Decimal('10.0'), Decimal('999999')),
        'sport_diversity': (Decimal('0.0'), Decimal('0.5')),
    }
    
    FANTASY_SIGNALS = {
        'cash_percentage': (Decimal('0.4'), Decimal('1.0')),
        'multi_entry_rate': (Decimal('3.0'), Decimal('999999')),
        'entries_per_week': (Decimal('20.0'), Decimal('999999')),
    }
    
    STATS_NERD_SIGNALS = {
        'sport_diversity': (Decimal('0.7'), Decimal('1.0')),
        'stake_variance': (Decimal('0.5'), Decimal('999999')),
        'avg_entry_fee': (Decimal('0.0'), Decimal('5.0')),
    }
    
    def score_personas(self, metrics: BehavioralMetrics) -> PersonaScore:
        """Calculate fit for each persona, return normalized scores"""
        
        bettor_score = self._score_bettor(metrics)
        fantasy_score = self._score_fantasy(metrics)
        stats_score = self._score_stats_nerd(metrics)
        
        # Normalize to sum to 1.0
        total = bettor_score + fantasy_score + stats_score
        if total == 0:
            # Default to stats_nerd if no signals
            return PersonaScore(
                bettor=Decimal('0.1'),
                fantasy=Decimal('0.1'),
                stats_nerd=Decimal('0.8')
            )
        
        return PersonaScore(
            bettor=bettor_score / total,
            fantasy=fantasy_score / total,
            stats_nerd=stats_score / total
        )
    
    def _score_bettor(self, metrics: BehavioralMetrics) -> Decimal:
        """Calculate bettor persona fit"""
        score = Decimal('0')
        
        # High GPP percentage
        score += self._score_in_range(
            metrics.gpp_percentage,
            self.BETTOR_SIGNALS['gpp_percentage']
        )
        
        # Higher stakes
        score += self._score_in_range(
            metrics.avg_entry_fee,
            self.BETTOR_SIGNALS['avg_entry_fee']
        )
        
        # Sport focus (inverse of diversity)
        score += self._score_in_range(
            metrics.sport_diversity,
            self.BETTOR_SIGNALS['sport_diversity']
        )
        
        return score
    
    def _score_fantasy(self, metrics: BehavioralMetrics) -> Decimal:
        """Calculate fantasy player persona fit"""
        score = Decimal('0')
        
        score += self._score_in_range(
            metrics.cash_percentage,
            self.FANTASY_SIGNALS['cash_percentage']
        )
        
        score += self._score_in_range(
            metrics.multi_entry_rate,
            self.FANTASY_SIGNALS['multi_entry_rate']
        )
        
        score += self._score_in_range(
            metrics.entries_per_week,
            self.FANTASY_SIGNALS['entries_per_week']
        )
        
        return score
    
    def _score_stats_nerd(self, metrics: BehavioralMetrics) -> Decimal:
        """Calculate stats nerd persona fit"""
        score = Decimal('0')
        
        score += self._score_in_range(
            metrics.sport_diversity,
            self.STATS_NERD_SIGNALS['sport_diversity']
        )
        
        score += self._score_in_range(
            metrics.stake_variance,
            self.STATS_NERD_SIGNALS['stake_variance']
        )
        
        score += self._score_in_range(
            metrics.avg_entry_fee,
            self.STATS_NERD_SIGNALS['avg_entry_fee']
        )
        
        return score
    
    def _score_in_range(
        self, 
        value: Decimal, 
        range_tuple: Tuple[Decimal, Decimal]
    ) -> Decimal:
        """Linear interpolation within range, 0 outside"""
        min_val, max_val = range_tuple
        
        if value < min_val:
            return Decimal('0')
        elif value > max_val:
            return Decimal('1.0')
        else:
            # Linear interpolation
            return (value - min_val) / (max_val - min_val)
```

**Acceptance Criteria:**
- ✅ Scores normalize to ~1.0
- ✅ Bettor sample → bettor > 0.6
- ✅ Fantasy sample → fantasy > 0.6
- ✅ Stats sample → stats_nerd > 0.6
- ✅ Performance: <50ms

**Test Coverage:** >90%

---

## Phase 5: Pattern Weight Mapping

**Goal:** Convert persona scores to pattern weights

### 5.1 Weight Mapper
**File:** `src/scoring/weight_mapper.py`

```python
from decimal import Decimal
from ..models.persona_score import PersonaScore
from ..models.pattern_weights import PatternWeights

class WeightMapper:
    """
    Convert persona scores to pattern detection weights.
    Why: Personalize insights without separate codebases.
    """
    
    BASE_WEIGHTS = PatternWeights()  # All 1.0
    
    BETTOR_MODIFIERS = PatternWeights(
        line_movement=Decimal('1.5'),
        live_odds_delta=Decimal('1.4'),
        injury_impact=Decimal('1.3'),
        historical_trends=Decimal('0.9'),
        player_correlations=Decimal('0.7'),
        contrarian_plays=Decimal('0.8'),
        weather_factors=Decimal('1.0'),
        situational_stats=Decimal('1.0'),
    )
    
    FANTASY_MODIFIERS = PatternWeights(
        player_correlations=Decimal('1.6'),
        injury_impact=Decimal('1.5'),
        situational_stats=Decimal('1.3'),
        contrarian_plays=Decimal('1.2'),
        line_movement=Decimal('0.8'),
        live_odds_delta=Decimal('0.6'),
        historical_trends=Decimal('1.0'),
        weather_factors=Decimal('1.1'),
    )
    
    STATS_NERD_MODIFIERS = PatternWeights(
        historical_trends=Decimal('1.5'),
        situational_stats=Decimal('1.6'),
        player_correlations=Decimal('1.4'),
        weather_factors=Decimal('1.3'),
        contrarian_plays=Decimal('1.3'),
        line_movement=Decimal('1.0'),
        injury_impact=Decimal('1.0'),
        live_odds_delta=Decimal('0.7'),
    )
    
    def calculate_weights(self, persona: PersonaScore) -> PatternWeights:
        """
        Weighted blend of modifiers based on persona scores.
        Example: 0.6 Bettor + 0.3 Fantasy + 0.1 Stats
        """
        
        # Start with base
        weights = {}
        
        # Blend each weight field
        for field in PatternWeights.model_fields.keys():
            bettor_val = getattr(self.BETTOR_MODIFIERS, field)
            fantasy_val = getattr(self.FANTASY_MODIFIERS, field)
            stats_val = getattr(self.STATS_NERD_MODIFIERS, field)
            
            blended = (
                bettor_val * persona.bettor +
                fantasy_val * persona.fantasy +
                stats_val * persona.stats_nerd
            )
            
            weights[field] = blended
        
        return PatternWeights(**weights)
```

**Acceptance Criteria:**
- ✅ Weighted blend works correctly
- ✅ Pure bettor → bettor modifiers
- ✅ Hybrid persona → proportional blend
- ✅ Performance: <10ms

**Test Coverage:** >90%

---

## Phase 6: Storage & API

**Goal:** Persist profiles and expose API

### 6.1 Profile Repository
**File:** `src/storage/profile_repository.py`

```python
from uuid import UUID
from typing import Optional
from ..models.user_profile import UserProfile
import psycopg2
from psycopg2.extras import Json

class ProfileRepository:
    """
    Persist and retrieve user profiles.
    Why: Enable cross-session, cross-app personalization.
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    def save_profile(self, profile: UserProfile) -> None:
        """Store user profile in database"""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_profiles (
                        user_id, created_at, updated_at,
                        total_entries_parsed, date_range_start, date_range_end,
                        platforms, behavioral_metrics, persona_bettor,
                        persona_fantasy, persona_stats_nerd, pattern_weights,
                        last_csv_upload, confidence_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        updated_at = EXCLUDED.updated_at,
                        total_entries_parsed = EXCLUDED.total_entries_parsed,
                        behavioral_metrics = EXCLUDED.behavioral_metrics,
                        persona_bettor = EXCLUDED.persona_bettor,
                        persona_fantasy = EXCLUDED.persona_fantasy,
                        persona_stats_nerd = EXCLUDED.persona_stats_nerd,
                        pattern_weights = EXCLUDED.pattern_weights,
                        last_csv_upload = EXCLUDED.last_csv_upload
                """, (
                    str(profile.user_id),
                    profile.created_at,
                    profile.updated_at,
                    profile.total_entries_parsed,
                    profile.date_range_start,
                    profile.date_range_end,
                    profile.platforms,
                    Json(profile.behavioral_metrics.model_dump()),
                    profile.persona_scores.bettor,
                    profile.persona_scores.fantasy,
                    profile.persona_scores.stats_nerd,
                    Json(profile.pattern_weights.model_dump()),
                    profile.last_csv_upload,
                    profile.confidence_score
                ))
                conn.commit()
    
    def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Retrieve user profile from database"""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM user_profiles WHERE user_id = %s
                """, (str(user_id),))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                # Reconstruct UserProfile from row
                # (Implementation would deserialize JSON fields)
                return None  # Placeholder
```

**Database Schema:**
```sql
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    total_entries_parsed INTEGER,
    date_range_start TIMESTAMP,
    date_range_end TIMESTAMP,
    platforms TEXT[],
    
    behavioral_metrics JSONB,
    
    persona_bettor DECIMAL(4,3),
    persona_fantasy DECIMAL(4,3),
    persona_stats_nerd DECIMAL(4,3),
    
    pattern_weights JSONB,
    
    last_csv_upload TIMESTAMP,
    confidence_score DECIMAL(4,3)
);

CREATE INDEX idx_user_profiles_updated ON user_profiles(updated_at);
```

**Acceptance Criteria:**
- ✅ Save profile without data loss
- ✅ Retrieve profile correctly
- ✅ Upsert handles duplicates
- ✅ Performance: <50ms

**Test Coverage:** >80% (integration tests)

---

## Performance Requirements

Claude Code must validate these benchmarks before considering the build complete:

| Operation | Target | Measurement Tool | Pass/Fail Criteria |
|-----------|--------|------------------|---------------------|
| Parse 10K entries | <500ms | pytest-benchmark | Avg time across 5 runs |
| Calculate behavioral metrics | <100ms | pytest-benchmark | Single execution time |
| Detect personas | <50ms | pytest-benchmark | Single execution time |
| Map pattern weights | <10ms | pytest-benchmark | Single execution time |
| Store user profile (DB) | <50ms | Direct timing | DB query time |
| Full pipeline (1K entries) | <2s | End-to-end test | Upload → weights ready |

**Performance Testing Commands:**
```bash
# Run benchmarks
pytest tests/unit --benchmark-only

# Verify against targets
pytest tests/benchmarks/test_performance.py -v

# Profile slow code
python -m cProfile -o profile.stats src/parsers/dfs_history_parser.py

# View profile results
python -m pstats profile.stats
```

**Why This Matters:**
- Fast parsing = better UX (<2s total is imperceptible)
- Low latency = lower Railway costs (CPU usage-based billing)
- Benchmarked = predictable scaling to 10K+ users

**Acceptance Criteria:**
- ✅ All performance tests pass
- ✅ No single operation exceeds 2x target time
- ✅ Benchmarks run in CI/CD pipeline

---

## Security Requirements

**Input Validation:**
```python
# Max file size check
MAX_CSV_SIZE = 10 * 1024 * 1024  # 10MB
if file_size > MAX_CSV_SIZE:
    raise ValueError("CSV file exceeds 10MB limit")

# Sanitize inputs
def sanitize_csv_input(value: str) -> str:
    """Remove potentially malicious characters"""
    # Strip SQL injection attempts
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
    for char in dangerous_chars:
        value = value.replace(char, "")
    return value.strip()
```

**Database Security:**
```python
# ALWAYS use parameterized queries
# ✅ CORRECT:
cursor.execute(
    "SELECT * FROM user_profiles WHERE user_id = %s",
    (user_id,)
)

# ❌ NEVER DO THIS:
cursor.execute(f"SELECT * FROM user_profiles WHERE user_id = '{user_id}'")
```

**Data Privacy:**
- CSV files: Process in memory, NEVER write to disk permanently
- User profiles: Store aggregates only, not individual entries
- Profile deletion: Hard delete on request (GDPR compliance)
- No cross-user data: Isolated queries, tenant-based filtering

**Dependency Security:**
```bash
# Run before deployment
pip-audit  # Check for known vulnerabilities
safety check  # Scan dependencies
bandit -r src/  # Static security analysis
```

**File Upload Security:**
- Accept only .csv extension
- Validate MIME type (text/csv)
- Scan for malicious content patterns
- Rate limit uploads (10 per hour per user)

**Secrets Management:**
```python
# Use environment variables, NEVER hardcode
import os
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not configured")
```

**Acceptance Criteria:**
- ✅ pip-audit shows 0 vulnerabilities
- ✅ bandit scan shows 0 high/medium issues
- ✅ All DB queries use parameterized syntax
- ✅ File size validation enforced
- ✅ Input sanitization on all CSV fields

---

## Required Performance Tests

Add these to `tests/benchmarks/test_performance.py`:

```python
import pytest
from decimal import Decimal
from datetime import datetime
from src.parsers.dfs_history_parser import DFSHistoryParser
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.persona_detector import PersonaDetector
from src.scoring.weight_mapper import WeightMapper

def generate_sample_csv(rows: int) -> str:
    """Generate sample CSV data for benchmarking"""
    lines = ["Entry ID,Contest Name,Entry Fee,Winnings,Sport,Date Entered,Points"]
    for i in range(rows):
        lines.append(f"{i},NFL GPP,3.00,5.50,NFL,2024-09-15 13:00:00,156.42")
    return "\n".join(lines)

def test_parse_performance(benchmark):
    """Parse 10K entries in <500ms"""
    csv_data = generate_sample_csv(rows=10_000)
    parser = DFSHistoryParser()
    
    result = benchmark(parser.parse_csv_string, csv_data)
    
    # Verify performance target
    assert benchmark.stats['mean'] < 0.5  # 500ms
    assert len(result) == 10_000

def test_metrics_calculation_performance(benchmark):
    """Calculate metrics in <100ms"""
    csv_data = generate_sample_csv(rows=1_000)
    parser = DFSHistoryParser()
    entries = parser.parse_csv_string(csv_data)
    
    scorer = BehavioralScorer()
    result = benchmark(scorer.calculate_metrics, entries)
    
    assert benchmark.stats['mean'] < 0.1  # 100ms

def test_persona_detection_performance(benchmark):
    """Detect persona in <50ms"""
    csv_data = generate_sample_csv(rows=1_000)
    parser = DFSHistoryParser()
    entries = parser.parse_csv_string(csv_data)
    scorer = BehavioralScorer()
    metrics = scorer.calculate_metrics(entries)
    
    detector = PersonaDetector()
    result = benchmark(detector.score_personas, metrics)
    
    assert benchmark.stats['mean'] < 0.05  # 50ms

def test_weight_mapping_performance(benchmark):
    """Map weights in <10ms"""
    from src.models.persona_score import PersonaScore
    persona = PersonaScore(
        bettor=Decimal("0.6"),
        fantasy=Decimal("0.3"),
        stats_nerd=Decimal("0.1")
    )
    
    mapper = WeightMapper()
    result = benchmark(mapper.calculate_weights, persona)
    
    assert benchmark.stats['mean'] < 0.01  # 10ms

def test_full_pipeline_performance(benchmark):
    """Full pipeline (1K entries) in <2s"""
    csv_data = generate_sample_csv(rows=1_000)
    
    def full_pipeline():
        parser = DFSHistoryParser()
        entries = parser.parse_csv_string(csv_data)
        
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(entries)
        
        detector = PersonaDetector()
        persona = detector.score_personas(metrics)
        
        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona)
        
        return weights
    
    result = benchmark(full_pipeline)
    assert benchmark.stats['mean'] < 2.0  # 2 seconds
```

---

## Required Security Tests

Add these to `tests/security/test_security.py`:

```python
import pytest
from src.parsers.dfs_history_parser import DFSHistoryParser
from src.utils.csv_validator import CSVValidator

def test_sql_injection_prevention():
    """Ensure malicious SQL is sanitized"""
    malicious_csv = """Entry ID,Contest Name,Entry Fee,Winnings,Sport,Date Entered,Points
1,'; DROP TABLE user_profiles; --,3.00,5.50,NFL,2024-09-15 13:00:00,156.42"""
    
    parser = DFSHistoryParser()
    entries = parser.parse_csv_string(malicious_csv)
    
    # Contest name should be sanitized
    assert "DROP TABLE" not in entries[0].contest_type
    assert ";" not in str(entries[0])

def test_file_size_limit():
    """Reject files over 10MB"""
    validator = CSVValidator()
    
    # Simulate large file (>10MB)
    large_csv = "x" * (11 * 1024 * 1024)  # 11MB
    
    with pytest.raises(ValueError, match="exceeds 10MB"):
        validator.validate_size(large_csv)

def test_csv_extension_validation():
    """Only accept .csv files"""
    validator = CSVValidator()
    
    assert validator.validate_extension("data.csv") == True
    assert validator.validate_extension("data.txt") == False
    assert validator.validate_extension("malicious.exe") == False

def test_decimal_for_money():
    """Ensure all money fields use Decimal, not float"""
    from src.models.dfs_entry import DFSEntry
    from decimal import Decimal
    from datetime import datetime
    
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
```

---

## Requirements

```
# Core dependencies
fastapi>=0.104.0
pydantic>=2.0.0
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-benchmark>=4.0.0

# Security
pip-audit>=2.6.1
safety>=2.3.5
bandit>=1.7.5

# Code quality
black>=23.10.0
isort>=5.12.0
mypy>=1.6.0
pylint>=3.0.0
```

---

## Build Order for Claude Code

**Night 1: Foundation (4-6 hours)**
1. ✅ Project structure setup
2. ✅ All models (Phase 1)
3. ✅ Unit tests for models
4. ✅ Run tests, verify >90% coverage

**Checkpoint:** All models pass tests

---

**Night 2: Parsing (4-6 hours)**
1. ✅ Contest classifier
2. ✅ CSV validator
3. ✅ DFS history parser
4. ✅ Create sample CSV fixtures
5. ✅ Unit tests for parsers
6. ✅ Security tests
7. ✅ Run tests, verify >90% coverage

**Checkpoint:** CSVs parse correctly into DFSEntry objects

---

**Night 3: Scoring & Detection (4-6 hours)**
1. ✅ Behavioral scorer
2. ✅ Persona detector
3. ✅ Weight mapper
4. ✅ Unit tests
5. ✅ Performance benchmarks
6. ✅ Run tests, verify >90% coverage

**Checkpoint:** Behavioral metrics → persona scores → pattern weights

---

**Night 4: Storage & Polish (4-6 hours)**
1. ✅ Profile repository
2. ✅ Integration tests (full pipeline)
3. ✅ All security tests pass
4. ✅ All performance benchmarks pass
5. ✅ Run pip-audit, safety, bandit
6. ✅ Code formatting (black, isort)
7. ✅ Type checking (mypy --strict)

**Checkpoint:** Production-ready microservice

---

## Success Metrics

**Technical:**
- ✅ All tests pass (>90% coverage)
- ✅ All performance targets met
- ✅ Zero security vulnerabilities
- ✅ mypy --strict passes
- ✅ black/isort formatted

**Business:**
- ✅ CSV upload → persona detection in <2s
- ✅ Ready for Railway deployment
- ✅ API endpoints documented
- ✅ Integration-ready for ThirdDownIQ

**User Experience:**
- ✅ Upload works for both DK and FD
- ✅ Persona detection is accurate
- ✅ Pattern weights make sense
- ✅ Error messages are clear

---

## Deployment (Post-Build)

```bash
# Local testing
docker-compose up

# Deploy to Railway
railway up

# Environment variables needed:
DATABASE_URL=postgresql://...
LOG_LEVEL=INFO
```

---

**Ready for autonomous Claude Code execution.**

Build order is clear, tests are specified, benchmarks are defined, security is enforced.
