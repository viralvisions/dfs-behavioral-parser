# Data Models - Design Specification

## Overview

This document defines the core data models for the DFS Behavioral Parser. These models represent the domain: what a DFS entry is, what behavioral patterns emerge, and how we personalize pattern detection.

---

## Model 1: DFSEntry

**Purpose:** Normalized representation of a single DFS contest entry from any platform.

**Location:** `src/models/dfs_entry.py`

### Fields

```python
@dataclass
class DFSEntry:
    entry_id: str              # Unique identifier (e.g., "12345")
    date: datetime             # When entry was made
    sport: str                 # Uppercase: NFL, NBA, NHL, MLB, etc.
    contest_type: str          # GPP, CASH, H2H, MULTI, UNKNOWN
    entry_fee: Decimal         # Amount wagered (use Decimal!)
    winnings: Decimal          # Amount won (use Decimal!)
    points: Decimal            # Fantasy points scored
    source: str                # "DRAFTKINGS" | "FANDUEL"
    contest_name: Optional[str] # Original contest name (for debugging)
```

### Why Decimal for Money?

**Problem with float:**
```python
entry_fee = 5.00  # Becomes 4.999999999
winnings = 10.50  # Becomes 10.499999999
profit = winnings - entry_fee  # Not exactly 5.50!
```

**Solution with Decimal:**
```python
entry_fee = Decimal('5.00')  # Exact
winnings = Decimal('10.50')   # Exact
profit = winnings - entry_fee # Decimal('5.50') - exact!
```

### Computed Properties

**roi** - Return on investment as percentage
```python
@property
def roi(self) -> Decimal:
    if self.entry_fee == 0:
        return Decimal('0')
    return ((self.winnings - self.entry_fee) / self.entry_fee) * 100
```

**profit** - Net profit/loss
```python
@property
def profit(self) -> Decimal:
    return self.winnings - self.entry_fee
```

**is_winning_entry** - Did this entry profit?
```python
@property
def is_winning_entry(self) -> bool:
    return self.winnings > self.entry_fee
```

### Validation

**In `__post_init__`:**
- Reject negative entry fees
- Reject negative winnings
- Reject invalid source (must be DRAFTKINGS or FANDUEL)
- Normalize sport to uppercase

### Example Usage

```python
entry = DFSEntry(
    entry_id="12345",
    date=datetime(2024, 9, 15, 13, 0),
    sport="nfl",  # Will be normalized to "NFL"
    contest_type="GPP",
    entry_fee=Decimal('5.00'),
    winnings=Decimal('10.50'),
    points=Decimal('156.42'),
    source="DRAFTKINGS",
    contest_name="NFL $20K Shot"
)

print(entry.roi)     # Decimal('110.00') - 110% ROI
print(entry.profit)  # Decimal('5.50')
print(entry.is_winning_entry)  # True
```

---

## Model 2: BehavioralMetrics

**Purpose:** Aggregated metrics calculated from a user's entire entry history.

**Location:** `src/models/behavioral_metrics.py`

### Volume Metrics

```python
total_entries: int                          # Total number of entries
entries_by_sport: Dict[str, int]            # {"NFL": 50, "NBA": 30, ...}
entries_by_contest_type: Dict[str, int]     # {"GPP": 40, "CASH": 25, ...}
```

### Financial Metrics

```python
total_invested: Decimal                     # Sum of all entry fees
total_winnings: Decimal                     # Sum of all winnings
avg_entry_fee: Decimal                      # Mean stake size
roi_overall: Decimal                        # Overall ROI percentage
```

**ROI Calculation:**
```python
net_profit = total_winnings - total_invested
roi_overall = (net_profit / total_invested) * 100
```

### Behavior Patterns (0.0 to 1.0 scale)

```python
gpp_percentage: Decimal                     # % entries in GPP tournaments
cash_percentage: Decimal                    # % entries in cash games
h2h_percentage: Decimal                     # % entries in head-to-head
multi_entry_rate: Decimal                   # Avg entries per unique contest
sport_diversity: Decimal                    # Shannon entropy (0=focused, 1=diverse)
stake_variance: Decimal                     # Coefficient of variation
```

**Sport Diversity (Shannon Entropy):**
```python
# Formula: H = -Σ(p_i * log2(p_i))
# Normalized to 0-1 scale

# Example:
# User A: 100 NFL entries → H ≈ 0 (focused)
# User B: 25 NFL, 25 NBA, 25 NHL, 25 MLB → H ≈ 1 (diverse)
```

**Stake Variance (Coefficient of Variation):**
```python
# Formula: CV = std_dev / mean

# Example:
# User A: Always bets $5 → CV ≈ 0 (consistent)
# User B: Bets $1, $5, $20, $50 → CV ≈ 0.8 (experimental)
```

### Temporal Patterns

```python
entries_per_week: Decimal                   # Avg entries per week
most_active_day: str                        # "Sunday", "Monday", etc.
recency_score: Decimal                      # Exponential decay weight
```

**Recency Score (Exponential Decay):**
```python
# Formula: Score = Σ(exp(-days_ago / 90))
# Half-life: 90 days

# Entry from yesterday: weight ≈ 0.99
# Entry from 3 months ago: weight ≈ 0.33
# Entry from 2 years ago: weight ≈ 0.01
```

### Data Quality

```python
confidence_score: Decimal                   # 0.0 to 1.0 based on completeness
```

**Confidence Calculation:**
```python
# Factor 1: Entry count (more = better)
count_score = min(total_entries / 50, 1.0)

# Factor 2: Recency (recent = better)
days_old = (now - most_recent_entry).days
recency_score = max(0, 1.0 - (days_old / 365))

# Factor 3: Contest diversity (varied = better)
diversity_score = len(unique_contest_types) / 4.0

# Weighted average
confidence = 0.5*count + 0.3*recency + 0.2*diversity
```

### Example

```python
metrics = BehavioralMetrics(
    total_entries=100,
    entries_by_sport={"NFL": 60, "NBA": 30, "NHL": 10},
    entries_by_contest_type={"GPP": 70, "CASH": 20, "H2H": 10},
    total_invested=Decimal('500.00'),
    total_winnings=Decimal('450.00'),
    avg_entry_fee=Decimal('5.00'),
    roi_overall=Decimal('-10.00'),  # -10% ROI
    gpp_percentage=Decimal('0.70'),
    cash_percentage=Decimal('0.20'),
    h2h_percentage=Decimal('0.10'),
    multi_entry_rate=Decimal('1.5'),
    sport_diversity=Decimal('0.65'),
    stake_variance=Decimal('0.40'),
    entries_per_week=Decimal('5.2'),
    most_active_day="Sunday",
    recency_score=Decimal('0.78'),
    confidence_score=Decimal('0.75')
)
```

---

## Model 3: PersonaScore

**Purpose:** Confidence scores for each persona archetype.

**Location:** `src/models/persona_score.py`

### Fields

```python
@dataclass
class PersonaScore:
    bettor: Decimal        # 0.0 to 1.0
    fantasy: Decimal       # 0.0 to 1.0
    stats_nerd: Decimal    # 0.0 to 1.0
```

**Constraint:** Scores must sum to 1.0 (normalized)

### Computed Properties

**primary_persona** - Highest scoring archetype
```python
@property
def primary_persona(self) -> str:
    scores = {
        'BETTOR': self.bettor,
        'FANTASY': self.fantasy,
        'STATS_NERD': self.stats_nerd,
    }
    return max(scores, key=scores.get)
```

**is_hybrid** - Multiple personas > 0.3 threshold
```python
@property
def is_hybrid(self) -> bool:
    high_scores = sum(
        1 for s in [self.bettor, self.fantasy, self.stats_nerd]
        if s > Decimal('0.3')
    )
    return high_scores >= 2
```

**confidence** - Spread between highest and lowest
```python
@property
def confidence(self) -> Decimal:
    max_score = max(self.bettor, self.fantasy, self.stats_nerd)
    min_score = min(self.bettor, self.fantasy, self.stats_nerd)
    return max_score - min_score
```

### Example Scenarios

**Pure Bettor:**
```python
PersonaScore(
    bettor=Decimal('0.85'),
    fantasy=Decimal('0.10'),
    stats_nerd=Decimal('0.05')
)
# primary_persona: "BETTOR"
# is_hybrid: False
# confidence: 0.80 (high)
```

**Hybrid (Bettor + Fantasy):**
```python
PersonaScore(
    bettor=Decimal('0.45'),
    fantasy=Decimal('0.40'),
    stats_nerd=Decimal('0.15')
)
# primary_persona: "BETTOR"
# is_hybrid: True (both > 0.3)
# confidence: 0.30 (low - close scores)
```

---

## Model 4: PatternWeights

**Purpose:** Multipliers for pattern detection algorithms.

**Location:** `src/models/pattern_weights.py`

### Fields (All default to 1.0)

```python
@dataclass
class PatternWeights:
    line_movement: Decimal         = Decimal('1.0')
    historical_trends: Decimal     = Decimal('1.0')
    injury_impact: Decimal         = Decimal('1.0')
    weather_factors: Decimal       = Decimal('1.0')
    player_correlations: Decimal   = Decimal('1.0')
    situational_stats: Decimal     = Decimal('1.0')
    live_odds_delta: Decimal       = Decimal('1.0')
    contrarian_plays: Decimal      = Decimal('1.0')
```

### Why These Patterns?

**line_movement** - Betting market shifts (Bettor priority)
- Example: Line moves from -3 to -4.5 (sharp money on favorite)

**historical_trends** - Long-term statistical patterns (Stats Nerd priority)
- Example: Team is 15-3 ATS after bye weeks

**injury_impact** - News-driven lineup changes (Fantasy priority)
- Example: RB1 out → backup RB sees 20+ touches

**weather_factors** - Environmental variables (Stats Nerd)
- Example: 25mph winds reduce passing yards 15%

**player_correlations** - Stacking strategies (Fantasy priority)
- Example: QB + WR1 correlation in DFS lineups

**situational_stats** - Context-specific performance (Stats Nerd)
- Example: WR averages 8 targets in slot vs man coverage

**live_odds_delta** - Real-time line shopping (Bettor priority)
- Example: Live total drops from 48.5 to 45 after slow start

**contrarian_plays** - Low-ownership opportunities (Fantasy/Stats)
- Example: Chalk RB at 40% ownership vs contrarian at 5%

### Methods

**apply_to_score** - Apply weight to base score
```python
def apply_to_score(self, pattern_name: str, base_score: Decimal) -> Decimal:
    weight = getattr(self, pattern_name)
    return base_score * weight
```

**to_dict / from_dict** - Serialization
```python
def to_dict(self) -> dict:
    return {field: str(getattr(self, field)) 
            for field in self.__dataclass_fields__}

@classmethod
def from_dict(cls, data: dict) -> 'PatternWeights':
    return cls(**{k: Decimal(v) for k, v in data.items()})
```

### Example: Bettor Weights

```python
weights = PatternWeights(
    line_movement=Decimal('1.5'),       # Prioritized
    live_odds_delta=Decimal('1.4'),     # Prioritized
    injury_impact=Decimal('1.3'),       # Important
    historical_trends=Decimal('0.9'),   # Deprioritized
    player_correlations=Decimal('0.7'), # Deprioritized
)

# Apply to a pattern score
base_score = Decimal('0.80')
weighted_score = weights.apply_to_score('line_movement', base_score)
# Result: Decimal('1.20') - boosted by 1.5x
```

---

## Data Flow

```
CSV File
    ↓
DFSEntry objects (normalized)
    ↓
BehavioralMetrics (aggregated)
    ↓
PersonaScore (detected)
    ↓
PatternWeights (personalized)
    ↓
ThirdDownIQ/ShotClockIQ/PowerPlayIQ
```

---

## Serialization Example

All models must serialize to JSON for API responses:

```python
# DFSEntry
entry.to_dict()
# {
#   'entry_id': '12345',
#   'sport': 'NFL',
#   'entry_fee': '5.00',
#   'winnings': '10.50',
#   'roi': '110.00',
#   'profit': '5.50',
#   ...
# }

# PersonaScore
persona.to_dict()
# {
#   'bettor': '0.271',
#   'fantasy': '0.144',
#   'stats_nerd': '0.586',
#   'primary_persona': 'STATS_NERD',
#   'is_hybrid': False,
#   'confidence': '0.442'
# }

# PatternWeights
weights.to_dict()
# {
#   'line_movement': '1.01',
#   'historical_trends': '1.27',
#   'injury_impact': '1.02',
#   ...
# }
```

---

## Validation Rules

### DFSEntry
- ❌ Negative entry_fee
- ❌ Negative winnings
- ❌ Invalid source (not DRAFTKINGS or FANDUEL)
- ✅ Sport normalized to uppercase

### PersonaScore
- ❌ Any score < 0 or > 1
- ✅ Scores sum to 1.0 (±0.001 tolerance)

### PatternWeights
- ❌ Negative weights
- ✅ All weights ≥ 0

### BehavioralMetrics
- ✅ All percentages in 0-1 range
- ✅ Counts ≥ 0
- ✅ Confidence score 0-1

---

## Testing Strategy

**Unit Tests for Each Model:**
1. Test field validation (reject invalid inputs)
2. Test computed properties (ROI, profit, etc.)
3. Test serialization (to_dict, from_dict)
4. Test edge cases (zero, single entry, extremes)

**Example Test:**
```python
def test_dfs_entry_roi_calculation():
    entry = DFSEntry(
        entry_id="test",
        date=datetime.now(),
        sport="NFL",
        contest_type="GPP",
        entry_fee=Decimal('10.00'),
        winnings=Decimal('25.00'),
        points=Decimal('150.00'),
        source="DRAFTKINGS"
    )
    
    assert entry.roi == Decimal('150.00')  # (25-10)/10 * 100 = 150%
    assert entry.profit == Decimal('15.00')
    assert entry.is_winning_entry == True
```

---

**These models are the foundation. Get them right, everything else follows.**
