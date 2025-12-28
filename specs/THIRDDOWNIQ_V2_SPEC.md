# ThirdDownIQ v2 - Claude Code Implementation Specification

## Project Overview

**Purpose:** NFL betting companion app that detects third down patterns, line movement, and live betting opportunities, with adaptive personalization based on user behavioral profiles from DFS history.

**Business Context:**
- Steve building autonomous revenue apps (99.8% margin target)
- Betting-focused, not intrigue/storytelling
- Template for ShotClockIQ (NBA) and PowerPlayIQ (NHL) clones
- Integrates with DFS Behavioral Parser for personalization
- Users get different insights based on Bettor/Fantasy/Stats Nerd persona

**Core Value Props by Persona:**
- **Bettor:** Line movement alerts, sharp money tracking, +EV opportunities
- **Fantasy Player:** Third down target volume, red zone usage, prop bet angles  
- **Stats Nerd:** Historical trends, situational analysis, correlation patterns

**Success Metrics:**
- Pattern detection latency: < 2s from game event to alert
- Line movement tracking: < 30s from odds change to notification
- User engagement: 5+ app opens per NFL Sunday
- Conversion: 20% free → paid ($9.99/month or $79/season)

---

## Technology Stack

**Backend:**
- Python 3.11+ (FastAPI for APIs)
- PostgreSQL 15+ (game data, user profiles, patterns)
- Redis (real-time caching, pub/sub for live updates)
- Celery (background jobs for pattern detection)

**Frontend:**
- React 18+ with TypeScript
- TailwindCSS (mobile-first)
- Recharts (data visualization)
- WebSockets (live updates)

**Data Sources:**
- The Odds API (odds feeds, line movement)
- ESPN API (game data, play-by-play)
- Pro Football Reference (historical stats)
- DFS Behavioral Parser (user personas)

**Infrastructure:**
- Docker (containerization)
- Railway/Render (deployment - cheap, auto-scaling)
- Cloudflare (CDN, DDoS protection)

---

## Integration with DFS Behavioral Parser

**User Flow:**
1. User uploads DFS CSV in onboarding
2. DFS Behavioral Parser processes → generates persona profile
3. ThirdDownIQ fetches persona via API
4. Pattern detection engines apply persona weights
5. UI shows personalized insights

**API Integration:**
```python
# In ThirdDownIQ backend
def get_user_persona(user_email: str) -> dict:
    """Fetch persona from DFS Parser microservice"""
    response = requests.get(
        f"{DFS_PARSER_API}/profiles/by-email/{user_email}"
    )
    return response.json()  # {persona_scores, pattern_weights}
```

---

## Build This First (Prerequisite)

**Complete DFS Behavioral Parser first** (from previous spec).

Once that's done, start ThirdDownIQ Phase 1.

---

## Phase 1: Foundation & Data Models

### Objective
Establish core data models for NFL games, odds, patterns, and user integration.

### Files to Create

#### 1.1 `backend/app/models/game.py`

**Purpose:** NFL game representation with live state tracking.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.database import Base

class GameStatus(str, Enum):
    """Game status states"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    HALFTIME = "halftime"
    FINAL = "final"
    POSTPONED = "postponed"

class NFLGame(Base):
    """
    NFL game with live state tracking.
    
    Why live state:
    - Pattern detection needs current game context
    - Live betting triggers depend on down/distance/score
    - User alerts tied to game flow
    """
    __tablename__ = 'nfl_games'
    
    game_id = Column(String, primary_key=True)  # e.g., "2024_01_KC_DET"
    season = Column(Integer, nullable=False)     # 2024
    week = Column(Integer, nullable=False)       # 1-18
    
    # Teams
    home_team = Column(String, nullable=False)   # "KC"
    away_team = Column(String, nullable=False)   # "DET"
    
    # Timing
    game_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default=GameStatus.SCHEDULED)
    
    # Score (live updated)
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)
    
    # Game state (live updated)
    quarter = Column(Integer, default=1)
    time_remaining = Column(String)              # "10:23"
    possession = Column(String)                  # "KC" or "DET"
    down = Column(Integer)                       # 1-4
    distance = Column(Integer)                   # Yards to first down
    yard_line = Column(Integer)                  # Field position (0-100)
    
    # Situational flags (computed)
    is_red_zone = Column(Boolean, default=False)       # < 20 yard line
    is_third_down = Column(Boolean, default=False)
    is_fourth_down = Column(Boolean, default=False)
    is_two_minute_drill = Column(Boolean, default=False)
    
    # Metadata
    weather = Column(JSON)                       # Temp, wind, conditions
    stadium = Column(String)
    
    # Relationships
    odds = relationship("GameOdds", back_populates="game")
    patterns = relationship("DetectedPattern", back_populates="game")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def update_game_state(self, play_data: dict):
        """
        Update live game state from play-by-play feed.
        
        Args:
            play_data: {
                'quarter': 2,
                'time': '10:23',
                'possession': 'KC',
                'down': 3,
                'distance': 7,
                'yard_line': 45,
                'home_score': 14,
                'away_score': 10
            }
        """
        self.quarter = play_data.get('quarter', self.quarter)
        self.time_remaining = play_data.get('time', self.time_remaining)
        self.possession = play_data.get('possession', self.possession)
        self.down = play_data.get('down', self.down)
        self.distance = play_data.get('distance', self.distance)
        self.yard_line = play_data.get('yard_line', self.yard_line)
        self.home_score = play_data.get('home_score', self.home_score)
        self.away_score = play_data.get('away_score', self.away_score)
        
        # Update computed flags
        self.is_red_zone = self.yard_line is not None and self.yard_line <= 20
        self.is_third_down = self.down == 3
        self.is_fourth_down = self.down == 4
        
        # Two minute drill: Q2 or Q4, < 2:00 remaining
        if self.time_remaining and self.quarter in [2, 4]:
            minutes, seconds = map(int, self.time_remaining.split(':'))
            self.is_two_minute_drill = (minutes * 60 + seconds) <= 120
        
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Serialize for API"""
        return {
            'game_id': self.game_id,
            'season': self.season,
            'week': self.week,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'game_time': self.game_time.isoformat() if self.game_time else None,
            'status': self.status,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'quarter': self.quarter,
            'time_remaining': self.time_remaining,
            'possession': self.possession,
            'down': self.down,
            'distance': self.distance,
            'yard_line': self.yard_line,
            'is_red_zone': self.is_red_zone,
            'is_third_down': self.is_third_down,
            'is_fourth_down': self.is_fourth_down,
            'is_two_minute_drill': self.is_two_minute_drill,
            'weather': self.weather,
            'stadium': self.stadium,
        }
```

**Tests Required:**
- Test update_game_state() updates all fields
- Test situational flags (red zone, third down, two-minute)
- Test to_dict() serialization

**Acceptance Criteria:**
- [ ] Game state updates work
- [ ] Situational flags computed correctly
- [ ] Serialization works

---

**[Continue with remaining models, services, engines, APIs, frontend...]**

**Note: This spec is too large for a single artifact. Break into phases:**
1. Models & Database (Phase 1)
2. Data Services (Phase 2)
3. Pattern Engines (Phase 3)
4. API Layer (Phase 4)
5. Frontend (Phase 5)
6. Workers & Deployment (Phase 6)

**Each phase builds on previous, with checkpoints.**

---

## MVP Feature Set (Launch Week 1)

**Must Have:**
- [ ] Live NFL games display
- [ ] Third down pattern detection
- [ ] Line movement tracking
- [ ] Basic persona integration (Bettor view)
- [ ] WebSocket live updates
- [ ] Mobile-responsive UI

**Nice to Have (Week 2):**
- [ ] Red zone patterns
- [ ] Full persona switching (Fantasy, Stats Nerd)
- [ ] Historical pattern library
- [ ] Push notifications

---

## Cloning to ShotClockIQ/PowerPlayIQ

**After ThirdDownIQ is live:**

1. **Copy codebase**
2. **Replace sport-specific code:**
   - NFL API → NBA/NHL API
   - Team names/abbreviations
   - Pattern engines (third down → end of quarter)
3. **Update branding/UI**
4. **Deploy as separate app**

**Shared:**
- User authentication
- Persona integration
- WebSocket infrastructure
- Pattern detection framework
- Subscription management

**Sport-specific:**
- Data sources
- Pattern algorithms
- Team/league constants
- UI terminology

---

## Estimated Build Time

**With Claude Code overnight sessions:**

**DFS Behavioral Parser:** 2-3 nights
**ThirdDownIQ v2:** 4-5 nights
**ShotClockIQ (clone):** 1-2 nights
**PowerPlayIQ (clone):** 1-2 nights

**Total: ~10 nights = 2 weeks of overnight builds**

**Your role during builds:**
- Review morning progress
- Test functionality
- Provide feedback/adjustments
- Handle deployment

---

## Revenue Model

**Subscription:**
- Free: Limited patterns, 3 games/week
- Premium: $9.99/month or $79/season (save $40)

**Target Metrics:**
- 1,000 users Year 1
- 20% conversion (200 paid)
- $79 avg/user = $15,800 ARR per app
- 3 apps × $15,800 = $47,400 total ARR
- 99.8% margins = $47,300 profit

**Cost Structure:**
- Hosting: ~$50/month ($600/year)
- APIs: ~$50/month ($600/year)
- Total: $1,200/year across all apps

**Actual margin: 97.5%**

---

**Ready to build. Give this spec to Claude Code and let it grind ThirdDownIQ v2 while you're on vacation this week.**
