# DFS Behavioral Parser

A Python microservice that parses DraftKings and FanDuel CSV transaction history to detect user personas and generate personalized pattern weights for downstream betting/DFS applications.

## Features

- **Multi-Platform CSV Parsing**: Auto-detects and parses both DraftKings and FanDuel export formats
- **Contest Classification**: Regex-based classification into GPP, CASH, H2H, and MULTI contest types
- **15+ Behavioral Metrics**: Volume, financial, temporal, and diversity metrics
- **Persona Detection**: Scores users against Bettor, Fantasy Player, and Stats Nerd archetypes
- **Pattern Weight Generation**: Personalized multipliers for pattern detection algorithms

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd dfs-behavioral-parser

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
# Run with sample data
python demo.py

# Run with your own CSV
python demo.py path/to/your/draftkings_export.csv
```

## Usage

### Python API

```python
from src.parsers import detect_platform, DraftKingsParser, FanDuelParser
from src.classifiers import ContestTypeClassifier
from src.scoring import calculate_metrics, score_personas, calculate_weights

# 1. Parse CSV
platform = detect_platform("export.csv")
parser = DraftKingsParser() if platform == "DRAFTKINGS" else FanDuelParser()
entries = parser.parse("export.csv")

# 2. Classify contests
classifier = ContestTypeClassifier()
classified = classifier.classify_entries(entries)

# 3. Calculate behavioral metrics
metrics = calculate_metrics(classified)

# 4. Detect persona
persona_score = score_personas(metrics)
print(f"Primary persona: {persona_score.primary_persona}")

# 5. Generate pattern weights
weights = calculate_weights(persona_score)
print(f"Top pattern: {weights.weights_ranked[0]}")
```

## Persona Archetypes

### Bettor (Tournament Grinder)
- High GPP percentage (70%+)
- Higher stakes ($10+)
- Focused on 1-2 sports
- Pattern priorities: line_movement, live_odds_delta

### Fantasy Player (Optimizer)
- High cash game percentage
- High multi-entry rate (3+ entries per contest)
- Volume player (20+ entries/week)
- Pattern priorities: player_correlations, injury_impact

### Stats Nerd (Researcher)
- High sport diversity (explores multiple sports)
- Variable stake sizes (experimental)
- Lower average stakes ($1-5)
- Pattern priorities: situational_stats, historical_trends

## Pattern Weights

| Pattern | Description | Bettor | Fantasy | Stats Nerd |
|---------|-------------|--------|---------|------------|
| line_movement | Betting line shifts | 1.5x | 0.8x | 0.7x |
| historical_trends | Long-term patterns | 0.9x | 1.1x | 1.5x |
| injury_impact | Lineup changes | 1.3x | 1.5x | 0.9x |
| weather_factors | Environmental | 0.8x | 1.0x | 1.3x |
| player_correlations | Stacking strategies | 0.7x | 1.6x | 1.2x |
| situational_stats | Context-specific | 1.0x | 1.3x | 1.6x |
| live_odds_delta | Real-time lines | 1.4x | 0.6x | 0.5x |
| contrarian_plays | Low-ownership | 1.1x | 1.4x | 1.3x |

## Project Structure

```
dfs-behavioral-parser/
├── src/
│   ├── models/           # Data models (DFSEntry, BehavioralMetrics, etc.)
│   ├── parsers/          # CSV parsers (DraftKings, FanDuel)
│   ├── classifiers/      # Contest type classification
│   ├── scoring/          # Behavioral scoring and persona detection
│   └── utils/            # Constants and utilities
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Sample CSV files
├── demo.py               # Working demonstration
└── requirements.txt
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run only unit tests
python -m pytest tests/unit/ -v

# Run only integration tests
python -m pytest tests/integration/ -v
```

**Current Status:** 164 tests passing in 0.68 seconds

## Technical Notes

### Decimal Precision
All financial calculations use Python's `Decimal` type to avoid floating-point precision errors. Never use `float` for money.

### Shannon Entropy
Sport diversity is calculated using Shannon entropy, normalized to 0-1:
- 0 = focused on one sport
- 1 = evenly distributed across many sports

### Exponential Decay
Recency scoring uses exponential decay with a 90-day half-life. Recent entries contribute more to behavioral analysis than older ones.

## Requirements

- Python 3.11+
- pandas >= 2.0.0
- python-dateutil >= 2.8.0
- pytest >= 7.0.0 (for testing)

## License

MIT
