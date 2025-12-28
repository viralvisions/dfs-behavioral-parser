# FantasyIQ Platform - Master Project Structure

## Overview

**Platform Name:** FantasyIQ.io
**Mission:** Personalized sports betting & DFS insights powered by behavioral analysis

**Components:**
1. DFS Behavioral Parser (microservice)
2. ThirdDownIQ (NFL app)
3. ShotClockIQ (NBA app - clone of ThirdDownIQ)
4. PowerPlayIQ (NHL app - clone of ThirdDownIQ)

**Pricing:**
- Free: Persona + 3 patterns/week
- Single Sport: $14.99/month ($119/year)
- All Sports: $29.99/month ($249/year)
- Elite: $49.99/month ($399/year)

---

## Project Repository Structure

```
fantasyiq-platform/
├── README.md
├── docs/
│   ├── 01-DFS-BEHAVIORAL-PARSER-SPEC.md
│   ├── 02-THIRDDOWNIQ-CORE-SPEC.md
│   ├── 03-THIRDDOWNIQ-MAGIC-LAYER-SPEC.md
│   ├── 04-SUBSCRIPTION-MANAGEMENT-SPEC.md
│   ├── architecture-overview.md
│   └── deployment-guide.md
│
├── services/
│   └── dfs-parser/                     # Microservice
│       ├── README.md
│       ├── requirements.txt
│       ├── docker-compose.yml
│       ├── src/
│       │   ├── models/
│       │   ├── parsers/
│       │   ├── classifiers/
│       │   ├── scoring/
│       │   └── api/
│       ├── tests/
│       └── alembic/
│
├── apps/
│   ├── thirddowniq/                    # NFL App
│   │   ├── README.md
│   │   ├── docker-compose.yml
│   │   ├── backend/
│   │   │   ├── requirements.txt
│   │   │   ├── app/
│   │   │   │   ├── models/
│   │   │   │   ├── services/
│   │   │   │   ├── pattern_engines/
│   │   │   │   ├── api/
│   │   │   │   └── workers/
│   │   │   └── tests/
│   │   └── frontend/
│   │       ├── package.json
│   │       ├── src/
│   │       │   ├── components/
│   │       │   ├── pages/
│   │       │   ├── hooks/
│   │       │   └── services/
│   │       └── public/
│   │
│   ├── shotclockiq/                    # NBA App (clone)
│   │   └── [same structure as thirddowniq]
│   │
│   └── powerplayiq/                    # NHL App (clone)
│       └── [same structure as thirddowniq]
│
├── shared/
│   ├── subscription-service/           # Shared Stripe/subscription logic
│   │   ├── src/
│   │   │   ├── stripe_client.py
│   │   │   ├── subscription_manager.py
│   │   │   └── webhook_handler.py
│   │   └── tests/
│   │
│   └── marketing-site/                 # FantasyIQ.io landing page
│       ├── index.html
│       ├── pricing.html
│       └── assets/
│
└── scripts/
    ├── deploy-parser.sh
    ├── deploy-nfl.sh
    ├── deploy-nba.sh
    └── deploy-nhl.sh
```

---

## Build Sequence

### **Week 1: Foundation**

**Days 1-3: DFS Behavioral Parser**
```bash
cd services/dfs-parser
# Give Claude Code: docs/01-DFS-BEHAVIORAL-PARSER-SPEC.md
# Output: Working microservice at localhost:5000
```

**Days 4-7: ThirdDownIQ Core**
```bash
cd apps/thirddowniq
# Give Claude Code: docs/02-THIRDDOWNIQ-CORE-SPEC.md
# Output: NFL app with basic patterns
```

### **Week 2: Magic Layer + Subscriptions**

**Days 8-11: Magic Layer Features**
```bash
cd apps/thirddowniq
# Give Claude Code: docs/03-THIRDDOWNIQ-MAGIC-LAYER-SPEC.md
# Output: Social proof, watchlist, correlations
```

**Days 12-14: Subscription System**
```bash
cd shared/subscription-service
# Give Claude Code: docs/04-SUBSCRIPTION-MANAGEMENT-SPEC.md
# Output: Stripe integration, paywall, tiers
```

### **Week 3: Clone & Deploy**

**Days 15-17: Clone to NBA/NHL**
```bash
# Copy thirddowniq → shotclockiq
# Swap NFL API for NBA API
# Update team names, constants
# Deploy

# Copy thirddowniq → powerplayiq
# Swap NFL API for NHL API
# Update team names, constants
# Deploy
```

**Days 18-21: Polish & Launch**
- Marketing site
- Bug fixes
- Performance tuning
- Go live

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│              FantasyIQ.io (Marketing)               │
│              Vercel (Static Site)                   │
└─────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ThirdDownIQ  │  │ ShotClockIQ  │  │ PowerPlayIQ  │
│ Frontend     │  │ Frontend     │  │ Frontend     │
│ Vercel       │  │ Vercel       │  │ Vercel       │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │     Shared API Gateway             │
        │     Railway (Load Balancer)        │
        └────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────────┐
        │                │                    │
        ▼                ▼                    ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│ ThirdDownIQ  │  │ ShotClockIQ  │  │ PowerPlayIQ     │
│ Backend      │  │ Backend      │  │ Backend         │
│ Railway      │  │ Railway      │  │ Railway         │
└──────────────┘  └──────────────┘  └─────────────────┘
        │                │                    │
        └────────────────┼────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌─────────────────────┐        ┌────────────────────┐
│ DFS Parser Service  │        │ Subscription Svc   │
│ Railway             │        │ Railway            │
│ parser-api.rail.app │        │ Stripe Integration │
└─────────────────────┘        └────────────────────┘
        │                                 │
        └────────────────┬────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │   PostgreSQL DB    │
              │   Railway          │
              └────────────────────┘
```

---

## Domain Setup

**Domains to Purchase:**
- fantasyiq.io → Marketing site
- thirddowniq.com → Redirects to fantasyiq.io/nfl
- shotclockiq.com → Redirects to fantasyiq.io/nba
- powerplayiq.com → Redirects to fantasyiq.io/nhl

**Or keep them separate:**
- thirddowniq.com → Standalone NFL app
- shotclockiq.com → Standalone NBA app
- powerplayiq.com → Standalone NHL app
- fantasyiq.io → Landing page that links to all three

**Recommended: Unified approach**
- fantasyiq.io is the main platform
- Sport-specific domains redirect there
- Single login, single subscription

---

## Environment Variables

**Each service needs:**

```bash
# DFS Parser
DATABASE_URL=postgresql://...
LOG_LEVEL=INFO

# ThirdDownIQ/ShotClockIQ/PowerPlayIQ
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
PARSER_API_URL=https://parser-api.railway.app
ODDS_API_KEY=your_key
ESPN_API_KEY=your_key
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_URL=https://fantasyiq.io

# Subscription Service
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
DATABASE_URL=postgresql://...
```

---

## Development Workflow

**1. Local Development:**
```bash
# Terminal 1: Start parser
cd services/dfs-parser
docker-compose up

# Terminal 2: Start NFL app backend
cd apps/thirddowniq/backend
uvicorn app.main:app --reload

# Terminal 3: Start NFL app frontend
cd apps/thirddowniq/frontend
npm run dev

# Access at:
# Parser: http://localhost:5000
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

**2. Testing:**
```bash
# Each service has its own tests
cd services/dfs-parser
pytest

cd apps/thirddowniq/backend
pytest

cd apps/thirddowniq/frontend
npm test
```

**3. Deployment:**
```bash
# Push to GitHub
git push origin main

# Railway auto-deploys:
# - services/dfs-parser → parser-api.railway.app
# - apps/thirddowniq/backend → thirddowniq-api.railway.app
# - shared/subscription-service → sub-api.railway.app

# Vercel auto-deploys:
# - apps/thirddowniq/frontend → thirddowniq.vercel.app (→ fantasyiq.io)
```

---

## Database Schema Overview

**DFS Parser Database:**
- user_profiles
- behavioral_metrics
- persona_scores
- pattern_weights

**Sports App Database (shared by NFL/NBA/NHL):**
- users
- games (nfl_games, nba_games, nhl_games)
- odds (game_odds)
- patterns (detected_patterns)
- watchlist_items
- bets
- user_activities (social proof)
- subscriptions

**Subscription Database:**
- stripe_customers
- stripe_subscriptions
- payment_history

---

## Monitoring & Analytics

**Production Monitoring:**
- Sentry (error tracking)
- PostHog (product analytics)
- Stripe Dashboard (revenue tracking)
- Railway Metrics (server performance)

**Key Metrics to Track:**
- User signups (free → paid conversion)
- Subscription tier distribution
- Pattern detection latency
- API response times
- User engagement (patterns viewed, bets tracked)
- Churn rate
- LTV (Lifetime Value)

---

## Cost Structure (Monthly)

**Infrastructure:**
- Railway (4 services): $80
- Vercel (3 frontends): $0 (hobby tier)
- PostgreSQL: Included in Railway
- Redis: Included in Railway
- The Odds API: $60
- Domain names: ~$10/month
- Stripe fees: ~3% of revenue
**Total Fixed: ~$150/month**

**At Scale (1,000 paid users):**
- Revenue: ~$20,000/month (avg $20/user)
- Costs: ~$750/month (includes Stripe fees)
- Profit: ~$19,250/month
- Margin: 96%

---

## Git Workflow

```bash
# Main branch: production
git checkout main

# Feature branches
git checkout -b feature/social-proof
git checkout -b feature/watchlist
git checkout -b feature/stripe-integration

# After testing
git checkout main
git merge feature/social-proof
git push origin main
# Railway auto-deploys
```

---

## Next Steps

1. **Create GitHub Organization:** `fantasyiq-platform`
2. **Create Repositories:**
   - `dfs-parser`
   - `thirddowniq`
   - `shotclockiq`
   - `powerplayiq`
   - `subscription-service`
   - `marketing-site`
3. **Connect to Railway:** Link repos for auto-deploy
4. **Connect to Vercel:** Link frontend repos
5. **Start Building:** Week 1, Day 1 - DFS Parser

---

**This structure scales from MVP to 10,000+ users without major refactoring.**
