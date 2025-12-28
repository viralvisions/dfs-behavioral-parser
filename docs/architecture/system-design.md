# System Architecture - DFS Behavioral Parser

## High-Level Overview

```
┌──────────────┐
│   User CSV   │
│ (DK or FD)   │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│ Platform Detector   │
│ (Identify DK/FD)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  CSV Parser         │
│  (DK or FD parser)  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ List[DFSEntry]      │
│ (Normalized data)   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Contest Classifier  │
│ (GPP/CASH/H2H/etc)  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Behavioral Scorer   │
│ (Calculate metrics) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ BehavioralMetrics   │
│ (15+ metrics)       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Persona Detector    │
│ (Score personas)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ PersonaScore        │
│ (Bettor/Fantasy/    │
│  Stats Nerd)        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Weight Mapper       │
│ (Blend modifiers)   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ PatternWeights      │
│ (Personalized       │
│  multipliers)       │
└─────────────────────┘
          │
          ▼
    Integration with
    ThirdDownIQ/etc
```

---

## Component Architecture

### Layer 1: Input Processing

**Components:**
- `platform_detector.py` - Identify CSV format
- `draftkings_parser.py` - Parse DK format
- `fanduel_parser.py` - Parse FD format
- `date_parser.py` - Flexible date parsing

**Responsibilities:**
- Validate CSV structure
- Clean currency/points data
- Handle date format variations
- Skip malformed rows
- Produce normalized DFSEntry objects

**Error Handling:**
- Invalid platform → ValueError with clear message
- Missing columns → ValueError listing required columns
- Malformed row → Log warning, skip row, continue
- Invalid date → ValueError with row number

---

### Layer 2: Classification

**Components:**
- `contest_type_classifier.py` - Pattern matching

**Responsibilities:**
- Classify contests using regex patterns
- Priority order: H2H → CASH → MULTI → GPP → UNKNOWN
- Batch processing support

**Why Regex (Not ML)?**
- Contest naming is consistent within platform
- New contest types appear monthly (ML would require retraining)
- Regex patterns are easily updateable
- Performance: O(n) vs ML inference overhead

---

### Layer 3: Behavioral Analysis

**Components:**
- `behavioral_scorer.py` - Calculate metrics

**Calculations:**

**Volume Metrics:**
```python
total_entries = len(entries)
entries_by_sport = Counter(e.sport for e in entries)
entries_by_contest_type = Counter(e.contest_type for e in entries)
```

**Financial Metrics:**
```python
total_invested = sum(e.entry_fee for e in entries)
total_winnings = sum(e.winnings for e in entries)
avg_entry_fee = total_invested / total_entries
roi_overall = ((total_winnings - total_invested) / total_invested) * 100
```

**Sport Diversity (Shannon Entropy):**
```python
import math

sport_counts = Counter(e.sport for e in entries)
total = len(entries)

entropy = 0.0
for count in sport_counts.values():
    if count > 0:
        p = count / total
        entropy -= p * math.log2(p)

# Normalize to 0-1
max_entropy = math.log2(len(sport_counts))
sport_diversity = entropy / max_entropy if max_entropy > 0 else 0
```

**Stake Variance (Coefficient of Variation):**
```python
import math

fees = [float(e.entry_fee) for e in entries]
mean = sum(fees) / len(fees)

variance = sum((x - mean) ** 2 for x in fees) / len(fees)
std_dev = math.sqrt(variance)

stake_variance = std_dev / mean if mean > 0 else 0
```

**Recency Score (Exponential Decay):**
```python
import math
from datetime import datetime

now = datetime.now()
half_life = 90  # days

total_weight = 0.0
for entry in entries:
    days_ago = (now - entry.date).days
    weight = math.exp(-days_ago / half_life)
    total_weight += weight

# Normalize
max_possible = len(entries)  # All entries today
recency_score = total_weight / max_possible
```

---

### Layer 4: Persona Detection

**Components:**
- `persona_detector.py` - Score archetypes

**Algorithm:**

```python
def score_persona(metrics: BehavioralMetrics, signals: dict) -> Decimal:
    """
    Score fit to persona based on signal matching.
    
    Args:
        metrics: User behavioral metrics
        signals: Dict of {metric_name: (min, max)}
    
    Returns:
        Raw score (0-1 range, before normalization)
    """
    scores = []
    
    for signal_name, (min_val, max_val) in signals.items():
        value = getattr(metrics, signal_name)
        
        # Linear interpolation
        if value < min_val:
            score = 0.0
        elif value > max_val:
            score = 1.0
        else:
            range_size = max_val - min_val
            if range_size == 0:
                score = 1.0
            else:
                score = (value - min_val) / range_size
        
        scores.append(score)
    
    # Average across signals
    return sum(scores) / len(scores)
```

**Normalization:**
```python
def normalize_scores(bettor_raw, fantasy_raw, stats_raw):
    """Normalize scores to sum to 1.0"""
    total = bettor_raw + fantasy_raw + stats_raw
    
    if total == 0:
        # Edge case: all zeros
        return (Decimal('0.33'), Decimal('0.33'), Decimal('0.34'))
    
    return (
        bettor_raw / total,
        fantasy_raw / total,
        stats_raw / total
    )
```

---

### Layer 5: Weight Generation

**Components:**
- `weight_mapper.py` - Blend modifiers

**Algorithm:**

```python
def calculate_weights(persona_scores: PersonaScore) -> PatternWeights:
    """
    Generate pattern weights from persona scores.
    
    Formula per pattern:
    weight = (bettor_score × bettor_modifier) +
             (fantasy_score × fantasy_modifier) +
             (stats_score × stats_modifier)
    """
    weights = {}
    
    for pattern_name in PATTERN_NAMES:
        bettor_mod = BETTOR_MODIFIERS[pattern_name]
        fantasy_mod = FANTASY_MODIFIERS[pattern_name]
        stats_mod = STATS_NERD_MODIFIERS[pattern_name]
        
        final_weight = (
            persona_scores.bettor * bettor_mod +
            persona_scores.fantasy * fantasy_mod +
            persona_scores.stats_nerd * stats_mod
        )
        
        weights[pattern_name] = final_weight
    
    return PatternWeights(**weights)
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────┐
│              CSV Upload                     │
│  (User uploads DraftKings/FanDuel CSV)      │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│         Platform Detection                  │
│  Input: CSV headers                         │
│  Output: "DRAFTKINGS" or "FANDUEL"          │
│  Error: ValueError if unknown format        │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│            CSV Parsing                      │
│  Input: CSV file + platform                 │
│  Output: List[DFSEntry]                     │
│  Process: Clean currency, parse dates       │
│  Error: Skip malformed rows with warning    │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│         Contest Classification              │
│  Input: DFSEntry.contest_name               │
│  Output: DFSEntry.contest_type              │
│  Process: Regex pattern matching            │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│       Behavioral Metric Calculation         │
│  Input: List[DFSEntry]                      │
│  Output: BehavioralMetrics                  │
│  Process:                                   │
│    - Volume aggregation                     │
│    - Financial calculations                 │
│    - Shannon entropy (diversity)            │
│    - Coefficient of variation (variance)    │
│    - Exponential decay (recency)            │
│    - Confidence scoring                     │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│         Persona Detection                   │
│  Input: BehavioralMetrics                   │
│  Output: PersonaScore                       │
│  Process:                                   │
│    - Score each persona (signal matching)   │
│    - Normalize scores (sum to 1.0)          │
│    - Determine primary & hybrid status      │
│    - Calculate confidence                   │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          Weight Generation                  │
│  Input: PersonaScore                        │
│  Output: PatternWeights                     │
│  Process: Blend modifiers by persona scores │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│           JSON Serialization                │
│  Output: {                                  │
│    user_id, persona_scores,                 │
│    pattern_weights, behavioral_metrics      │
│  }                                          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
        Integration with Apps
        (ThirdDownIQ, etc.)
```

---

## Technology Choices

### Why Python?
- Fast development (dataclasses, type hints)
- Rich ecosystem (pandas for CSV parsing)
- Easy integration with ML/data science tools (future)
- Steve's familiarity

### Why pandas?
- CSV parsing is battle-tested
- Handles encoding issues automatically
- Fast for large datasets (10K+ rows)

### Why Decimal (Not float)?
- Financial precision required
- Avoids rounding errors ($5.50 must be exactly $5.50)
- Industry standard for money calculations

### Why Shannon Entropy?
- Well-established metric for diversity
- Normalized 0-1 scale
- Captures concentration vs exploration behavior

### Why Exponential Decay?
- Recent behavior more predictive than old
- Smooth weighting (not binary)
- Standard approach in time-series analysis

### Why Linear Interpolation for Signals?
- Simple, interpretable
- Gradual scoring (not binary yes/no)
- Easy to tune ranges

---

## Performance Considerations

### Current Implementation (MVP)
- **Target:** Parse 10K entries in < 500ms
- **Approach:** Simple loops, no optimization
- **Bottleneck:** Shannon entropy calculation (O(n log n))

### Future Optimizations (If Needed)

**Batch Processing:**
```python
# Instead of processing one user at a time
for user in users:
    parse_csv(user.csv_file)

# Process in batches
entries = parse_all_csvs(user_csv_files)  # Parallel
metrics = calculate_metrics_batch(entries)  # Vectorized
```

**Caching:**
```python
# Cache parsed CSVs for repeat users
@lru_cache(maxsize=1000)
def parse_csv(csv_hash: str):
    ...
```

**Database Indexing (Future):**
```sql
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_updated_at ON user_profiles(updated_at);
```

---

## Error Handling Strategy

### Validation Errors (User Fixable)
```python
# Missing required columns
raise ValueError("Missing required columns: ['Entry Fee', 'Winnings']")

# Invalid data types
raise ValueError("Row 15: Cannot parse date '2024-13-45'")
```

### Data Quality Warnings (Non-Fatal)
```python
# Malformed row
logger.warning(f"Row {idx}: Skipping due to missing Sport field")

# Unknown contest type
logger.warning(f"Row {idx}: Unknown contest type '{name}', defaulting to UNKNOWN")
```

### System Errors (Developer Fixable)
```python
# Programming errors
raise AssertionError("Persona scores do not sum to 1.0")

# Unexpected state
raise RuntimeError("No entries after parsing - this should never happen")
```

---

## Testing Strategy

### Unit Tests (90%+ coverage)
- Test each model independently
- Test each calculation function
- Test edge cases (zero, one, many)

### Integration Tests
- Test full parsing pipeline
- Test full scoring pipeline
- Test end-to-end (CSV → weights)

### Performance Tests
```python
def test_performance_10k_entries():
    """Ensure parsing 10K entries < 500ms"""
    import time
    
    start = time.time()
    entries = parse_csv('fixtures/large_dataset.csv')
    elapsed = time.time() - start
    
    assert len(entries) == 10000
    assert elapsed < 0.5  # 500ms
```

---

## Future Architecture (Not MVP)

### API Layer (Phase 5)
```python
from fastapi import FastAPI, UploadFile

app = FastAPI()

@app.post("/parse")
async def parse_csv(file: UploadFile):
    """
    Upload CSV, get persona profile.
    
    Returns:
        {
            user_id, persona_scores,
            pattern_weights, behavioral_metrics,
            confidence_score
        }
    """
    # Process in-memory (privacy)
    contents = await file.read()
    entries = parse_csv_bytes(contents)
    
    # Score
    metrics = calculate_metrics(entries)
    personas = detect_personas(metrics)
    weights = generate_weights(personas)
    
    # Save profile (not CSV)
    profile = save_profile(user_id, metrics, personas, weights)
    
    return profile.to_dict()
```

### Database Schema (Phase 6)
```sql
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- Summary
    total_entries INTEGER,
    date_range_start TIMESTAMP,
    date_range_end TIMESTAMP,
    platforms TEXT[],  -- ["DRAFTKINGS", "FANDUEL"]
    
    -- Metrics (stored as JSONB)
    behavioral_metrics JSONB,
    
    -- Personas (indexed for querying)
    persona_bettor DECIMAL(4, 3),
    persona_fantasy DECIMAL(4, 3),
    persona_stats_nerd DECIMAL(4, 3),
    
    -- Weights (stored as JSONB)
    pattern_weights JSONB,
    
    -- Quality
    confidence_score DECIMAL(4, 3),
    last_csv_upload TIMESTAMP
);

CREATE INDEX idx_user_profiles_updated ON user_profiles(updated_at);
CREATE INDEX idx_user_profiles_confidence ON user_profiles(confidence_score);
```

---

**This architecture supports MVP → production scaling without major refactoring.**
