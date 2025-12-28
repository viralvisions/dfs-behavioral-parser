# Complete Setup Guide - DFS Behavioral Parser

## What You're Building

A Python microservice that:
1. Parses DraftKings/FanDuel CSVs (your DFS history)
2. Calculates behavioral metrics (ROI, sport diversity, etc.)
3. Detects your persona (Bettor/Fantasy/Stats Nerd)
4. Generates personalized pattern weights for ThirdDownIQ

**Build Time:** 2-3 hours (Claude Code builds while you sleep)

---

## Quick Start (5 Minutes)

### Step 1: Create Project Folder

**On Windows:**
```batch
# Run this in Command Prompt or PowerShell
mkdir C:\Users\ebgne\dfs-behavioral-parser
cd C:\Users\ebgne\dfs-behavioral-parser

# Create docs structure
mkdir docs
mkdir docs\design
mkdir docs\future  
mkdir docs\architecture
```

**On Mac/Linux:**
```bash
mkdir -p ~/dfs-behavioral-parser/docs/{design,future,architecture}
cd ~/dfs-behavioral-parser
```

---

### Step 2: Copy Documentation Files

Copy all files from this package into your project:

```
C:\Users\ebgne\dfs-behavioral-parser\
├── docs\
│   ├── CLAUDE_CODE_PROMPT.md       ← Main build prompt
│   ├── feature-list.json           ← Feature breakdown
│   ├── claude.md                   ← Claude instructions
│   ├── roadmap.md                  ← Build phases
│   ├── design\
│   │   ├── data-models.md          ← Model specifications
│   │   └── persona-signals.md      ← Detection logic
│   ├── future\
│   │   └── (empty for now)
│   └── architecture\
│       └── system-design.md        ← Architecture overview
```

---

### Step 3: Open in Claude Code

1. **Open Claude Code desktop app**
2. **File → Open Folder**
3. **Select:** `C:\Users\ebgne\dfs-behavioral-parser`
4. **Claude Code will automatically read all `/docs` files**

---

### Step 4: Give Claude Code the Build Prompt

**Copy this exact text and paste into Claude Code:**

```
I need you to build the DFS Behavioral Parser microservice.

Please read:
- /docs/CLAUDE_CODE_PROMPT.md (main instructions)
- /docs/feature-list.json (complete feature list)
- /docs/claude.md (context and approach)
- /docs/roadmap.md (build phases)
- /docs/design/data-models.md (model specs)
- /docs/design/persona-signals.md (detection logic)
- /docs/architecture/system-design.md (architecture)

Start with Phase 1 (Foundation & Data Models), then Phase 2 (CSV Parsing), then Phase 3 (Intelligence Layer).

Build incrementally. Test after each phase. Let's get this working!
```

---

### Step 5: Let Claude Code Build

Claude Code will:
- ✅ Read all documentation
- ✅ Create project structure
- ✅ Write all code files
- ✅ Create tests
- ✅ Run tests after each phase
- ✅ Create demo.py

**Expected timeline:**
- Phase 1: ~30 min
- Phase 2: ~20 min
- Phase 3: ~30 min
- Testing & polish: ~20 min

**Total: ~2 hours**

---

## What Claude Code Will Create

```
C:\Users\ebgne\dfs-behavioral-parser\
├── README.md
├── requirements.txt
├── demo.py
├── src\
│   ├── __init__.py
│   ├── models\
│   │   ├── __init__.py
│   │   ├── dfs_entry.py
│   │   ├── behavioral_metrics.py
│   │   ├── persona_score.py
│   │   └── pattern_weights.py
│   ├── parsers\
│   │   ├── __init__.py
│   │   ├── base_parser.py
│   │   ├── platform_detector.py
│   │   ├── draftkings_parser.py
│   │   └── fanduel_parser.py
│   ├── classifiers\
│   │   ├── __init__.py
│   │   └── contest_type_classifier.py
│   ├── scoring\
│   │   ├── __init__.py
│   │   ├── behavioral_scorer.py
│   │   ├── persona_detector.py
│   │   └── weight_mapper.py
│   └── utils\
│       ├── __init__.py
│       ├── constants.py
│       └── date_parser.py
└── tests\
    ├── __init__.py
    ├── unit\
    │   ├── test_models.py
    │   ├── test_parsers.py
    │   ├── test_classifiers.py
    │   └── test_scoring.py
    ├── integration\
    │   ├── test_parsing_pipeline.py
    │   └── test_end_to_end.py
    └── fixtures\
        ├── sample_draftkings.csv
        ├── sample_fanduel.csv
        └── sample_edge_cases.csv
```

---

## After Claude Code Finishes

### Verify the Build

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (should see 37+ passing)
pytest tests/ -v

# Run demo (should see complete output)
python demo.py
```

### Expected Demo Output

```
=== DFS Behavioral Parser Demo ===

[1] Parsing CSV...
    ✓ Detected platform: DRAFTKINGS
    ✓ Parsed 8 entries
    ✓ Date range: 2024-09-08 to 2024-10-24

[2] Classifying contests...
    ✓ GPP: 3 entries
    ✓ CASH: 2 entries
    ✓ H2H: 1 entry

[3] Calculating behavioral metrics...
    ✓ Total invested: $65.00
    ✓ Total winnings: $65.80
    ✓ Overall ROI: 1.2%
    ✓ Sport diversity: 0.89 (very diverse)

[4] Detecting personas...
    ✓ STATS_NERD: 58.6% (PRIMARY)
    ✓ BETTOR: 27.1%
    ✓ FANTASY: 14.4%

[5] Generating pattern weights...
    ✓ situational_stats: 1.39x
    ✓ historical_trends: 1.27x
    ✓ player_correlations: 1.24x

=== Complete! ===
```

---

## Troubleshooting

### "Claude Code seems stuck"
→ Ask: "What's the status? What files have you created?"
→ Say: "Please continue with the next phase"

### "Tests are failing"
→ Check Python version: `python --version` (need 3.11+)
→ Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
→ Ask Claude Code: "Why are tests failing? Show me the error"

### "Import errors"
→ Check for missing `__init__.py` files
→ Ask Claude Code: "Add missing __init__.py files"

### "Performance issues"
→ Check dataset size (should be < 10K entries for MVP)
→ Ask Claude Code: "Optimize for larger datasets"

---

## Testing with Your Own Data

### Get Your DFS History

**DraftKings:**
1. Log in to DraftKings.com
2. Account → History → Contest History
3. Export to CSV
4. Save as `my_dk_history.csv`

**FanDuel:**
1. Log in to FanDuel.com
2. Account → My Contests → Export
3. Save as `my_fd_history.csv`

### Run Parser

```python
from src.parsers.platform_detector import PlatformDetector
from src.parsers.draftkings_parser import DraftKingsParser
from src.parsers.fanduel_parser import FanDuelParser
from src.classifiers.contest_type_classifier import ContestTypeClassifier
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.persona_detector import PersonaDetector
from src.scoring.weight_mapper import WeightMapper

# Detect platform
with open('my_dk_history.csv') as f:
    columns = f.readline().strip().split(',')

detector = PlatformDetector()
platform = detector.detect(columns)
print(f"Platform: {platform}")

# Parse CSV
if platform == "DRAFTKINGS":
    parser = DraftKingsParser()
else:
    parser = FanDuelParser()

entries = parser.parse_csv('my_dk_history.csv')
print(f"Parsed {len(entries)} entries")

# Classify contests
classifier = ContestTypeClassifier()
for entry in entries:
    entry.contest_type = classifier.classify(entry.contest_name)

# Calculate metrics
scorer = BehavioralScorer()
metrics = scorer.calculate_metrics(entries)
print(f"ROI: {metrics.roi_overall:.2f}%")
print(f"Sport diversity: {metrics.sport_diversity:.2f}")

# Detect personas
detector = PersonaDetector()
personas = detector.score_personas(metrics)
print(f"Primary persona: {personas.primary_persona}")
print(f"Bettor: {personas.bettor:.1%}")
print(f"Fantasy: {personas.fantasy:.1%}")
print(f"Stats Nerd: {personas.stats_nerd:.1%}")

# Generate weights
mapper = WeightMapper()
weights = mapper.calculate_weights(personas)
print("\nPattern Weights:")
for pattern, weight in weights.to_dict().items():
    print(f"  {pattern}: {weight}")
```

---

## Next Steps After Build

1. **Test with your DFS history**
2. **Adjust persona signals if needed** (edit `docs/design/persona-signals.md`)
3. **Deploy to Railway** (optional, for API access)
4. **Integrate with ThirdDownIQ** (Night 4-5)

---

## Support

**If you hit issues:**
1. Check `/docs` files for context
2. Ask Claude Code specific questions
3. Review test failures for clues
4. Check the original spec in `/mnt/project/`

**Common fixes:**
- Missing dependencies → `pip install -r requirements.txt`
- Import errors → Add `__init__.py` files
- Test failures → Check edge cases in test files

---

## Project Files Reference

| File | Purpose |
|------|---------|
| `CLAUDE_CODE_PROMPT.md` | Main build instructions for Claude Code |
| `feature-list.json` | Complete feature breakdown with acceptance criteria |
| `claude.md` | Context, approach, common questions |
| `roadmap.md` | Phase-by-phase build plan |
| `design/data-models.md` | Model specifications and examples |
| `design/persona-signals.md` | Detection logic and signal ranges |
| `architecture/system-design.md` | System architecture and data flow |

---

## Success Criteria

**You'll know it's working when:**
- ✅ All tests passing (37+ tests)
- ✅ Demo.py runs successfully
- ✅ Your CSV parses correctly
- ✅ Persona detection feels accurate
- ✅ Pattern weights differ by persona

**Performance targets:**
- Parse 10K entries in < 500ms
- Full pipeline in < 1 second
- Test suite in < 5 seconds

---

## Ready to Start?

1. ✅ Create folders (`C:\Users\ebgne\dfs-behavioral-parser`)
2. ✅ Copy docs files
3. ✅ Open in Claude Code
4. ✅ Give build prompt
5. ✅ Let Claude Code build!

**Estimated time to working parser: 2 hours**

**Let's build! 🚀**
