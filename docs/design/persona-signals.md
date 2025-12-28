# Persona Signals - Detection Logic

## Overview

This document defines how we detect user personas from behavioral metrics. Each persona has "signals" (behavioral indicators) that, when present, increase the confidence that a user matches that archetype.

---

## The Three Personas

### 1. Bettor (Tournament Grinder)
**Psychology:** "I'm here to hit the jackpot. I study matchups, find edges, and bet big on my convictions."

**Playstyle:**
- Enters high-stakes GPP tournaments
- Focused on 1-2 sports (specialization)
- Low multi-entry (believes in "the one perfect lineup")
- Willing to risk more for higher upside

**Use Case:** Sports betting companion apps (ThirdDownIQ)

---

### 2. Fantasy Player (DFS Optimizer)
**Psychology:** "I grind volume. I use optimizers. I stack correlations. I want consistent profit, not moonshots."

**Playstyle:**
- Loves cash games (50/50, double-ups)
- High multi-entry (3-20 lineups per contest)
- Volume player (20+ entries/week)
- Uses optimizers and lineup builders

**Use Case:** DFS lineup optimization tools

---

### 3. Stats Nerd (Data Explorer)
**Psychology:** "I'm here to learn. I test theories. I explore different sports. It's not about profit, it's about understanding the game."

**Playstyle:**
- Plays many sports (high diversity)
- Experimental stakes (varies widely)
- Low stakes ($0.25-$5 entries)
- Tries different strategies

**Use Case:** Analytics dashboards, research tools

---

## Signal Ranges

Signals are defined as ranges of behavioral metrics. If a user's metric falls within the range, they get a score for that persona.

### Bettor Signals

```python
BETTOR_SIGNALS = {
    'gpp_percentage': (Decimal('0.7'), Decimal('1.0')),
    # 70-100% of entries in GPP tournaments
    # Why: Bettors chase big scores, not consistent cash
    
    'avg_entry_fee': (Decimal('10.0'), Decimal('999999')),
    # $10+ average stakes
    # Why: Willing to risk more for higher upside
    
    'sport_diversity': (Decimal('0.0'), Decimal('0.5')),
    # Low diversity (focused on 1-2 sports)
    # Why: Specialization = edge
    
    'multi_entry_rate': (Decimal('1.0'), Decimal('2.0')),
    # 1-2 entries per contest
    # Why: "Single bullet" mentality
}
```

**Scoring Logic:**
Linear interpolation within range
```python
# Example: User's GPP% = 0.85
# Range: 0.7 to 1.0
# Score: (0.85 - 0.7) / (1.0 - 0.7) = 0.5

# Example: User's GPP% = 0.95
# Range: 0.7 to 1.0  
# Score: (0.95 - 0.7) / (1.0 - 0.7) = 0.83
```

**Pattern Priorities (Modifiers):**
```python
BETTOR_MODIFIERS = {
    'line_movement': Decimal('1.5'),      # Show me where sharp money is
    'live_odds_delta': Decimal('1.4'),    # Live betting opportunities
    'injury_impact': Decimal('1.3'),      # Breaking news = edge
    'historical_trends': Decimal('0.9'),  # Less interested
    'player_correlations': Decimal('0.7'), # Not relevant
}
```

---

### Fantasy Player Signals

```python
FANTASY_SIGNALS = {
    'cash_percentage': (Decimal('0.4'), Decimal('1.0')),
    # 40-100% of entries in cash games
    # Why: Grinders prefer consistent profit over lottery tickets
    
    'multi_entry_rate': (Decimal('3.0'), Decimal('999999')),
    # 3+ entries per contest
    # Why: Optimizer mentality (multiple lineups to cover variance)
    
    'entries_per_week': (Decimal('20.0'), Decimal('999999')),
    # 20+ entries per week
    # Why: Volume players
    
    'roi_overall': (Decimal('-20.0'), Decimal('20.0')),
    # -20% to +20% ROI
    # Why: Grinding volume means lower ROI variance
}
```

**Scoring Logic:**
Same linear interpolation
```python
# Example: User's multi_entry_rate = 8.0
# Range: 3.0 to 999999
# Since upper bound is very high, any value > 3.0 scores highly
# Score: min((8.0 - 3.0) / (999999 - 3.0), 1.0) ≈ 0.99
```

**Pattern Priorities (Modifiers):**
```python
FANTASY_MODIFIERS = {
    'player_correlations': Decimal('1.6'),  # QB-WR stacks
    'injury_impact': Decimal('1.5'),        # Backup RB value
    'situational_stats': Decimal('1.3'),    # Red zone targets
    'contrarian_plays': Decimal('1.2'),     # Low ownership
    'line_movement': Decimal('0.8'),        # Less relevant
    'live_odds_delta': Decimal('0.6'),      # Not relevant
}
```

---

### Stats Nerd Signals

```python
STATS_NERD_SIGNALS = {
    'sport_diversity': (Decimal('0.7'), Decimal('1.0')),
    # 70-100% diversity (plays many sports)
    # Why: Curiosity-driven, not specialization
    
    'stake_variance': (Decimal('0.5'), Decimal('999999')),
    # High variance in stakes
    # Why: Experimenting with different strategies
    
    'avg_entry_fee': (Decimal('0.0'), Decimal('5.0')),
    # Low stakes ($0-$5)
    # Why: It's about learning, not profit
}
```

**Scoring Logic:**
Same linear interpolation
```python
# Example: User's sport_diversity = 0.89
# Range: 0.7 to 1.0
# Score: (0.89 - 0.7) / (1.0 - 0.7) = 0.63
```

**Pattern Priorities (Modifiers):**
```python
STATS_NERD_MODIFIERS = {
    'situational_stats': Decimal('1.6'),     # Deep analytics
    'historical_trends': Decimal('1.5'),     # Historical context
    'player_correlations': Decimal('1.4'),   # Statistical relationships
    'weather_factors': Decimal('1.3'),       # Environmental impact
    'contrarian_plays': Decimal('1.3'),      # Unique angles
    'line_movement': Decimal('1.0'),         # Neutral
    'live_odds_delta': Decimal('0.7'),       # Less relevant
}
```

---

## Persona Detection Algorithm

### Step 1: Score Each Persona

For each persona:
1. Extract signals (e.g., BETTOR_SIGNALS)
2. For each signal, calculate fit score (linear interpolation)
3. Average all signal scores
4. Result: Raw score for that persona

**Example:**
```python
# User metrics
metrics = {
    'gpp_percentage': 0.85,
    'avg_entry_fee': 25.00,
    'sport_diversity': 0.35,
    'multi_entry_rate': 1.5,
}

# Score Bettor persona
bettor_scores = []

# Signal 1: GPP%
signal = (0.85 - 0.7) / (1.0 - 0.7) = 0.50
bettor_scores.append(0.50)

# Signal 2: Avg entry fee
signal = (25 - 10) / (999999 - 10) ≈ 1.0
bettor_scores.append(1.0)

# Signal 3: Sport diversity
signal = (0.35 - 0.0) / (0.5 - 0.0) = 0.70
bettor_scores.append(0.70)

# Signal 4: Multi-entry rate
signal = (1.5 - 1.0) / (2.0 - 1.0) = 0.50
bettor_scores.append(0.50)

# Average
bettor_raw_score = (0.50 + 1.0 + 0.70 + 0.50) / 4 = 0.675
```

### Step 2: Normalize Scores

Scores must sum to 1.0:

```python
bettor_raw = 0.675
fantasy_raw = 0.210
stats_nerd_raw = 0.315

total = 0.675 + 0.210 + 0.315 = 1.20

bettor_final = 0.675 / 1.20 = 0.563 (56.3%)
fantasy_final = 0.210 / 1.20 = 0.175 (17.5%)
stats_nerd_final = 0.315 / 1.20 = 0.263 (26.3%)

# Verify: 0.563 + 0.175 + 0.263 = 1.001 ≈ 1.0 ✓
```

### Step 3: Determine Primary Persona

```python
primary = max(bettor, fantasy, stats_nerd)
# "BETTOR" (56.3%)
```

### Step 4: Check for Hybrid

```python
HYBRID_THRESHOLD = 0.3

high_scores = [
    bettor_final > 0.3,    # True (0.563)
    fantasy_final > 0.3,   # False (0.175)
    stats_nerd_final > 0.3 # False (0.263)
]

is_hybrid = sum(high_scores) >= 2
# False - only one persona > 0.3
```

### Step 5: Calculate Confidence

```python
confidence = max_score - min_score
# 0.563 - 0.175 = 0.388

# High spread = high confidence in primary persona
# Low spread = user is between personas (hybrid)
```

---

## Edge Cases

### Case 1: Insufficient Data
**Scenario:** User uploaded 5 entries
**Challenge:** Not enough data to confidently detect persona

**Solution:**
```python
confidence_score = calculate_confidence(metrics)
# Based on: entry count, recency, diversity
# Result: 0.15 (low)

# Still detect persona, but flag low confidence
persona_scores = detect_personas(metrics)
# {
#   'bettor': 0.40,
#   'fantasy': 0.35,
#   'stats_nerd': 0.25,
#   'confidence': 0.15  # LOW - warn user
# }
```

### Case 2: True Hybrid
**Scenario:** User is 45% Bettor, 40% Fantasy, 15% Stats Nerd
**Challenge:** No clear primary persona

**Solution:**
```python
is_hybrid = True  # Both > 0.3
primary = "BETTOR"  # Highest, but close
confidence = 0.30  # Low (close scores)

# Pattern weights will blend modifiers proportionally
weights = {
    'line_movement': 0.45*1.5 + 0.40*0.8 + 0.15*1.0 = 1.145
    # Blend: Bettor wants 1.5x, Fantasy wants 0.8x, Stats wants 1.0x
}
```

### Case 3: All Signals Weak
**Scenario:** User doesn't match any persona strongly
**Challenge:** Raw scores all low

**Solution:**
```python
# Raw scores
bettor_raw = 0.15
fantasy_raw = 0.10
stats_nerd_raw = 0.12

# Still normalize
total = 0.37
bettor = 0.15 / 0.37 = 0.405
fantasy = 0.10 / 0.37 = 0.270
stats_nerd = 0.12 / 0.37 = 0.324

# Primary: BETTOR (40.5%)
# Confidence: 0.405 - 0.270 = 0.135 (VERY LOW)
# Message to user: "Based on limited data, you seem like a Bettor, but we're not very confident. Upload more entries for better personalization."
```

---

## Pattern Weight Generation

Once persona is detected, generate pattern weights by blending modifiers:

```python
def calculate_weights(persona_scores: PersonaScore) -> PatternWeights:
    weights = {}
    
    for pattern in PATTERNS:
        bettor_mod = BETTOR_MODIFIERS[pattern]
        fantasy_mod = FANTASY_MODIFIERS[pattern]
        stats_mod = STATS_NERD_MODIFIERS[pattern]
        
        final_weight = (
            persona_scores.bettor * bettor_mod +
            persona_scores.fantasy * fantasy_mod +
            persona_scores.stats_nerd * stats_mod
        )
        
        weights[pattern] = final_weight
    
    return PatternWeights(**weights)
```

**Example:**
```python
# Persona: 56% Bettor, 18% Fantasy, 26% Stats Nerd

# line_movement weight
final = 0.56*1.5 + 0.18*0.8 + 0.26*1.0
      = 0.84 + 0.144 + 0.26
      = 1.244

# situational_stats weight
final = 0.56*1.0 + 0.18*1.3 + 0.26*1.6
      = 0.56 + 0.234 + 0.416
      = 1.21

# Result: line_movement slightly higher priority than situational_stats
```

---

## Tuning Signals

Signals can be adjusted based on user feedback:

**Current Ranges (MVP):**
- BETTOR avg_entry_fee: $10+
- FANTASY entries_per_week: 20+
- STATS_NERD sport_diversity: 0.7+

**If Users Report Misclassification:**

Option 1: Adjust range thresholds
```python
# Old
'avg_entry_fee': (Decimal('10.0'), Decimal('999999'))

# New (more permissive)
'avg_entry_fee': (Decimal('5.0'), Decimal('999999'))
```

Option 2: Add new signals
```python
# Add to BETTOR_SIGNALS
'h2h_percentage': (Decimal('0.0'), Decimal('0.2'))
# Bettors avoid H2H (not +EV)
```

Option 3: Adjust signal weights
```python
# Currently all signals equally weighted
# Could add weights:
BETTOR_SIGNALS_WEIGHTED = {
    ('gpp_percentage', 2.0),      # 2x weight
    ('avg_entry_fee', 1.5),       # 1.5x weight
    ('sport_diversity', 1.0),     # 1x weight
    ('multi_entry_rate', 1.0),    # 1x weight
}
```

---

## Testing Persona Detection

### Test Case 1: Pure Bettor
```python
metrics = BehavioralMetrics(
    gpp_percentage=Decimal('0.95'),
    avg_entry_fee=Decimal('50.00'),
    sport_diversity=Decimal('0.25'),
    multi_entry_rate=Decimal('1.1'),
    ...
)

personas = detect_personas(metrics)
assert personas.primary_persona == "BETTOR"
assert personas.bettor > Decimal('0.80')
assert personas.is_hybrid == False
```

### Test Case 2: Hybrid (Bettor + Fantasy)
```python
metrics = BehavioralMetrics(
    gpp_percentage=Decimal('0.60'),
    cash_percentage=Decimal('0.30'),
    multi_entry_rate=Decimal('4.5'),
    entries_per_week=Decimal('25'),
    ...
)

personas = detect_personas(metrics)
assert personas.is_hybrid == True
assert personas.bettor > Decimal('0.30')
assert personas.fantasy > Decimal('0.30')
```

### Test Case 3: Stats Nerd
```python
metrics = BehavioralMetrics(
    sport_diversity=Decimal('0.92'),
    avg_entry_fee=Decimal('2.50'),
    stake_variance=Decimal('0.85'),
    ...
)

personas = detect_personas(metrics)
assert personas.primary_persona == "STATS_NERD"
assert personas.stats_nerd > Decimal('0.60')
```

---

**Signals define personas. Personas define weights. Weights personalize apps. This is the intelligence layer.**
