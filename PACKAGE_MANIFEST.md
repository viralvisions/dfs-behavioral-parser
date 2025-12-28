# Claude Code Setup Package - File Manifest

## Package Contents

This package contains everything you need to build the DFS Behavioral Parser with Claude Code.

---

## Core Documentation Files

### Main Instructions
- **COMPLETE_SETUP_GUIDE.md** - Start here! Step-by-step setup
- **CLAUDE_CODE_PROMPT.md** - The exact prompt to give Claude Code
- **SETUP_FOR_WINDOWS.bat** - Windows batch script to create folders

### Project Documentation
- **docs/feature-list.json** - Complete feature breakdown with acceptance criteria
- **docs/claude.md** - Instructions for Claude Code (context, approach, Q&A)
- **docs/roadmap.md** - Phase-by-phase build plan with milestones

### Design Documentation
- **docs/design/data-models.md** - Model specifications (DFSEntry, BehavioralMetrics, etc.)
- **docs/design/persona-signals.md** - Persona detection logic and signal ranges

### Architecture Documentation
- **docs/architecture/system-design.md** - System architecture and data flow diagrams

---

## How to Use This Package

### Quick Start (Windows)

1. **Run the setup script:**
   ```
   Double-click SETUP_FOR_WINDOWS.bat
   ```
   This creates: `C:\Users\ebgne\dfs-behavioral-parser\docs\{design,future,architecture}`

2. **Copy all files from this package into:**
   ```
   C:\Users\ebgne\dfs-behavioral-parser\docs\
   ```

3. **Open Claude Code:**
   - Open folder: `C:\Users\ebgne\dfs-behavioral-parser`
   - Claude Code auto-reads `/docs`

4. **Give Claude Code the build prompt:**
   - Open `docs/CLAUDE_CODE_PROMPT.md`
   - Copy the entire prompt
   - Paste into Claude Code chat
   - Let it build!

### Quick Start (Mac/Linux)

```bash
# Create structure
mkdir -p ~/dfs-behavioral-parser/docs/{design,future,architecture}
cd ~/dfs-behavioral-parser

# Copy all docs files into docs/

# Open in Claude Code
# Give it the prompt from CLAUDE_CODE_PROMPT.md
```

---

## What Claude Code Will Build

### Project Structure
```
dfs-behavioral-parser/
├── README.md
├── requirements.txt
├── demo.py
├── src/
│   ├── models/        (4 files)
│   ├── parsers/       (4 files)
│   ├── classifiers/   (1 file)
│   ├── scoring/       (3 files)
│   └── utils/         (2 files)
└── tests/
    ├── unit/          (4 test files)
    ├── integration/   (2 test files)
    └── fixtures/      (3 CSV samples)
```

### Total Files Created: ~25 Python files

### Test Coverage: 37+ tests, 80%+ coverage

### Build Time: 2-3 hours (autonomous)

---

## After Build Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run tests: `pytest tests/ -v` (expect 37+ passing)
- [ ] Run demo: `python demo.py` (expect full output)
- [ ] Test with your CSV (DraftKings or FanDuel)
- [ ] Verify persona detection feels accurate
- [ ] Check pattern weights differ by persona

---

## Expected Demo Output

```
=== DFS Behavioral Parser Demo ===

[1] Parsing CSV...
    ✓ Detected platform: DRAFTKINGS
    ✓ Parsed 8 entries (2024-09-08 to 2024-10-24)

[2] Classifying contests...
    ✓ GPP: 3, CASH: 2, H2H: 1, MULTI: 1

[3] Behavioral Metrics
    • Total invested: $65.00
    • Total winnings: $65.80
    • Overall ROI: 1.2%
    • Sport diversity: 0.89 (very diverse)
    • Confidence: 0.42

[4] Persona Detection
    PRIMARY: STATS_NERD (58.6%)
    Secondary: BETTOR (27.1%)
    Tertiary: FANTASY (14.4%)

[5] Pattern Weights
    • situational_stats: 1.39x
    • historical_trends: 1.27x
    • player_correlations: 1.24x
    (8 total pattern weights)

=== Complete! ===
```

---

## Documentation Reading Order

**For Claude Code (automatic):**
Claude Code reads all `/docs` files automatically when you open the folder.

**For You (manual review):**
1. **COMPLETE_SETUP_GUIDE.md** - Start here
2. **docs/claude.md** - Understand the approach
3. **docs/roadmap.md** - See the build phases
4. **docs/design/data-models.md** - Understand the models
5. **docs/design/persona-signals.md** - Understand detection logic
6. **docs/architecture/system-design.md** - See the big picture

---

## Troubleshooting

**Claude Code seems stuck:**
- Ask: "What's the status?"
- Say: "Show me what files you've created"
- Say: "Continue with the next phase"

**Tests failing:**
- Check Python version: `python --version` (need 3.11+)
- Reinstall: `pip install -r requirements.txt --force-reinstall`
- Ask Claude Code: "Why are tests failing?"

**Import errors:**
- Missing `__init__.py` files
- Ask Claude Code: "Add missing __init__.py files"

---

## Next Steps After Build

1. **Week 1 Complete:** DFS Parser working
2. **Week 2:** Build ThirdDownIQ (NFL app)
3. **Week 3:** Clone to ShotClockIQ (NBA) and PowerPlayIQ (NHL)
4. **Week 4:** Add subscriptions, deploy, launch!

---

## Support Resources

- Original spec: `/mnt/project/DFS_BEHAVIORAL_PARSER_SPEC.md`
- ThirdDownIQ spec: `/mnt/project/THIRDDOWNIQ_V2_SPEC.md`
- Master structure: `/mnt/project/00-MASTER-PROJECT-STRUCTURE.md`

---

## File Sizes

| File | Size | Purpose |
|------|------|---------|
| COMPLETE_SETUP_GUIDE.md | ~8 KB | Main setup instructions |
| CLAUDE_CODE_PROMPT.md | ~6 KB | Build prompt for Claude Code |
| docs/feature-list.json | ~4 KB | Feature breakdown |
| docs/claude.md | ~10 KB | Context and approach |
| docs/roadmap.md | ~6 KB | Build phases |
| docs/design/data-models.md | ~12 KB | Model specifications |
| docs/design/persona-signals.md | ~10 KB | Detection logic |
| docs/architecture/system-design.md | ~10 KB | Architecture overview |

**Total package: ~66 KB** (small, easy to transfer)

---

## Success Metrics

**Phase 1-3 (This Build):**
- ✅ 37+ tests passing
- ✅ 80%+ code coverage
- ✅ Demo works end-to-end
- ✅ Performance targets met
- ✅ All acceptance criteria met

**Integration (Week 2):**
- ✅ ThirdDownIQ calls parser successfully
- ✅ Persona detection >85% accuracy
- ✅ Users satisfied with personalization

---

## Ready to Build!

**Your next action:**
1. Run `SETUP_FOR_WINDOWS.bat` (or create folders manually)
2. Copy all files from this package into `/docs`
3. Open folder in Claude Code
4. Give it the prompt from `CLAUDE_CODE_PROMPT.md`
5. Let Claude Code build while you relax!

**Estimated time: 2-3 hours autonomous building**

🚀 **Let's ship this!**
