# ThirdDownIQ v2 - NFL Betting Companion Spec

## Overview
**Purpose:** NFL betting companion app that provides personalized insights based on user's DFS behavioral profile (Bettor/Fantasy/Stats Nerd personas detected by DFS Parser).

**Key Features:**
- Real-time NFL game tracking
- Live odds ingestion from The Odds API
- Third down pattern detection (efficiency, conversion rates, situational analysis)
- Persona-weighted pattern display
- Adaptive UI based on user type

**Architecture:** Python/FastAPI backend + React frontend, deployed to Railway + Vercel

---

## System Architecture

```
┌─────────────────────────────────────┐
│   ThirdDownIQ Frontend (React)      │
│   Vercel: thirddowniq.vercel.app    │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   ThirdDownIQ Backend (FastAPI)     │
│   Railway: thirddowniq-api.rail.app │
└─────────────────────────────────────┘
          │              │
    ┌─────┴────┐    ┌────┴────────┐
    ▼          ▼    ▼             ▼
┌───────┐  ┌────────┐  ┌─────────────────┐
│Parser │  │The Odds│  │ESPN NFL API     │
│  API  │  │  API   │  │(game data)      │
└───────┘  └────────┘  └─────────────────┘
```

---

## Phase 1: Data Models

### 1.1 NFL Game Model
**File:** `backend/app/models/nfl_game.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class NFLGame(BaseModel):
    """
    NFL game with current state.
    Why: Track live games for pattern detection.
    """
    game_id: str
    home_team: str
    away_team: str
    start_time: datetime
    status: Literal["scheduled", "live", "final"]
    
    # Live game state
    quarter: Optional[int] = None
    time_remaining: Optional[str] = None
    home_score: int = 0
    away_score: int = 0
    possession: Optional[str] = None
    down: Optional[int] = None
    distance: Optional[int] = None
    yard_line: Optional[int] = None
    
    # Metadata
    week: int
    season: int
```

### 1.2 Game Odds Model
**File:** `backend/app/models/game_odds.py`

```python
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Literal

class GameOdds(BaseModel):
    """
    Betting odds for a game from a specific sportsbook.
    Why: Track line movement for sharp money detection.
    """
    game_id: str
    sportsbook: str  # "draftkings", "fanduel", "betmgm"
    timestamp: datetime
    
    # Spread
    home_spread: Decimal
    home_spread_odds: int  # American odds (-110)
    away_spread: Decimal
    away_spread_odds: int
    
    # Total
    total: Decimal
    over_odds: int
    under_odds: int
    
    # Moneyline
    home_ml: int
    away_ml: int
```

### 1.3 Third Down Pattern Model
**File:** `backend/app/models/third_down_pattern.py`

```python
from pydantic import BaseModel
from decimal import Decimal
from typing import Literal

class ThirdDownPattern(BaseModel):
    """
    Detected third down efficiency pattern.
    Why: Core betting insight for ThirdDownIQ.
    """
    game_id: str
    team: str
    pattern_type: Literal["efficiency", "conversion_rate", "red_zone", "two_minute"]
    
    # Metrics
    attempts: int
    conversions: int
    conversion_rate: Decimal  # 0.0 to 1.0
    
    # Situational
    distance_range: str  # "short" (1-3), "medium" (4-6), "long" (7+)
    field_position: str  # "own_territory", "midfield", "red_zone"
    
    # Betting relevance
    variance_from_avg: Decimal  # % above/below league avg
    confidence_score: Decimal  # 0.0 to 1.0
    
    # Persona weights applied
    weight_applied: Decimal
```

---

## Phase 2: External Services Integration

### 2.1 The Odds API Service
**File:** `backend/app/services/odds_service.py`

```python
import requests
from typing import List
from ..models.game_odds import GameOdds
from datetime import datetime
from decimal import Decimal

class OddsAPIService:
    """
    Fetch live betting odds from The Odds API.
    Why: Core data source for line movement detection.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
    
    def get_nfl_odds(self) -> List[GameOdds]:
        """
        Fetch current NFL odds from all sportsbooks.
        Returns: List of GameOdds objects
        """
        response = requests.get(
            f"{self.base_url}/sports/americanfootball_nfl/odds",
            params={
                "apiKey": self.api_key,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Odds API error: {response.status_code}")
        
        data = response.json()
        return self._parse_odds(data)
    
    def _parse_odds(self, data: dict) -> List[GameOdds]:
        """Convert API response to GameOdds objects"""
        odds_list = []
        
        for game in data:
            game_id = game["id"]
            
            for bookmaker in game.get("bookmakers", []):
                sportsbook = bookmaker["key"]
                
                # Extract spreads, totals, moneylines
                # (Implementation details)
                
                odds = GameOdds(
                    game_id=game_id,
                    sportsbook=sportsbook,
                    timestamp=datetime.utcnow(),
                    # ... populate fields
                )
                odds_list.append(odds)
        
        return odds_list
```

**Acceptance Criteria:**
- ✅ Fetches odds from DraftKings, FanDuel, BetMGM
- ✅ Updates every 30 seconds during game days
- ✅ Stores historical snapshots for line movement
- ✅ Rate limit: 500 requests/month (free tier)

### 2.2 ESPN NFL API Service
**File:** `backend/app/services/espn_service.py`

```python
import requests
from typing import List
from ..models.nfl_game import NFLGame
from datetime import datetime

class ESPNService:
    """
    Fetch live NFL game data from ESPN API.
    Why: Track down/distance/field position for pattern detection.
    """
    
    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    
    def get_live_games(self) -> List[NFLGame]:
        """Get all games in progress"""
        response = requests.get(f"{self.base_url}/scoreboard")
        data = response.json()
        
        games = []
        for event in data.get("events", []):
            if event["status"]["type"]["state"] == "in":
                games.append(self._parse_game(event))
        
        return games
    
    def _parse_game(self, event: dict) -> NFLGame:
        """Convert ESPN event to NFLGame"""
        competitions = event["competitions"][0]
        
        return NFLGame(
            game_id=event["id"],
            home_team=competitions["competitors"][0]["team"]["abbreviation"],
            away_team=competitions["competitors"][1]["team"]["abbreviation"],
            start_time=datetime.fromisoformat(event["date"]),
            status="live",
            quarter=event["status"]["period"],
            time_remaining=event["status"]["displayClock"],
            home_score=int(competitions["competitors"][0]["score"]),
            away_score=int(competitions["competitors"][1]["score"]),
            # Parse situation data if available
            down=self._extract_down(event),
            distance=self._extract_distance(event),
            yard_line=self._extract_yard_line(event),
            week=event["week"]["number"],
            season=event["season"]["year"]
        )
```

**Acceptance Criteria:**
- ✅ Updates every 10 seconds during live games
- ✅ Extracts down/distance/yard line
- ✅ Handles missing data gracefully
- ✅ Free API, no rate limits

---

## Phase 3: Pattern Detection Engine

### 3.1 Third Down Analyzer
**File:** `backend/app/pattern_engines/third_down_analyzer.py`

```python
from decimal import Decimal
from typing import List
from ..models.nfl_game import NFLGame
from ..models.third_down_pattern import ThirdDownPattern

class ThirdDownAnalyzer:
    """
    Detect third down efficiency patterns in NFL games.
    Why: Core insight for betting decisions.
    """
    
    # League averages (2024 season)
    LEAGUE_AVG_CONVERSION = Decimal("0.41")  # 41%
    
    def analyze_game(self, game: NFLGame, historical_data: dict) -> List[ThirdDownPattern]:
        """
        Analyze third down performance for both teams.
        Returns: List of detected patterns
        """
        patterns = []
        
        # Home team analysis
        home_pattern = self._analyze_team(
            game.game_id,
            game.home_team,
            historical_data[game.home_team]
        )
        if home_pattern:
            patterns.append(home_pattern)
        
        # Away team analysis
        away_pattern = self._analyze_team(
            game.game_id,
            game.away_team,
            historical_data[game.away_team]
        )
        if away_pattern:
            patterns.append(away_pattern)
        
        return patterns
    
    def _analyze_team(self, game_id: str, team: str, data: dict) -> ThirdDownPattern:
        """Analyze single team's third down performance"""
        
        # Extract metrics
        attempts = data.get("third_down_attempts", 0)
        conversions = data.get("third_down_conversions", 0)
        
        if attempts == 0:
            return None
        
        conversion_rate = Decimal(conversions) / Decimal(attempts)
        variance = ((conversion_rate - self.LEAGUE_AVG_CONVERSION) / 
                   self.LEAGUE_AVG_CONVERSION) * 100
        
        # Only flag significant variance (>10%)
        if abs(variance) < Decimal("10"):
            return None
        
        return ThirdDownPattern(
            game_id=game_id,
            team=team,
            pattern_type="efficiency",
            attempts=attempts,
            conversions=conversions,
            conversion_rate=conversion_rate,
            distance_range=self._classify_distance(data),
            field_position=self._classify_field_position(data),
            variance_from_avg=variance,
            confidence_score=self._calculate_confidence(attempts),
            weight_applied=Decimal("1.0")  # Applied later by persona
        )
    
    def _calculate_confidence(self, sample_size: int) -> Decimal:
        """Higher sample = higher confidence"""
        if sample_size >= 20:
            return Decimal("0.9")
        elif sample_size >= 10:
            return Decimal("0.7")
        else:
            return Decimal("0.5")
```

**Acceptance Criteria:**
- ✅ Detects patterns with >10% variance from league avg
- ✅ Confidence score based on sample size
- ✅ Handles edge cases (0 attempts, incomplete data)
- ✅ Performance: <50ms per game

---

## Phase 4: Persona Integration

### 4.1 DFS Parser Client
**File:** `backend/app/services/parser_client.py`

```python
import requests
from typing import Optional

class ParserClient:
    """
    Client for DFS Behavioral Parser API.
    Why: Fetch user persona to weight patterns.
    """
    
    def __init__(self, parser_url: str):
        self.parser_url = parser_url
    
    def get_user_persona(self, user_id: str) -> Optional[dict]:
        """
        Fetch user's persona profile from parser.
        Returns: PersonaScore + PatternWeights
        """
        response = requests.get(f"{self.parser_url}/profile/{user_id}")
        
        if response.status_code == 404:
            # User hasn't uploaded CSV yet
            return None
        
        if response.status_code != 200:
            raise Exception(f"Parser API error: {response.status_code}")
        
        return response.json()
```

### 4.2 Pattern Weighting Service
**File:** `backend/app/services/pattern_weighter.py`

```python
from decimal import Decimal
from typing import List
from ..models.third_down_pattern import ThirdDownPattern

class PatternWeighter:
    """
    Apply persona weights to detected patterns.
    Why: Personalize insights without separate codebases.
    """
    
    def apply_weights(
        self, 
        patterns: List[ThirdDownPattern], 
        pattern_weights: dict
    ) -> List[ThirdDownPattern]:
        """
        Multiply pattern confidence by persona weight.
        Bettor sees line_movement patterns boosted.
        Fantasy sees player_correlations boosted.
        """
        
        for pattern in patterns:
            # Get weight for this pattern type
            weight_key = self._map_pattern_to_weight(pattern.pattern_type)
            weight = Decimal(str(pattern_weights.get(weight_key, 1.0)))
            
            # Apply weight
            pattern.weight_applied = weight
            pattern.confidence_score = pattern.confidence_score * weight
        
        # Re-sort by weighted confidence
        patterns.sort(key=lambda p: p.confidence_score, reverse=True)
        
        return patterns
    
    def _map_pattern_to_weight(self, pattern_type: str) -> str:
        """Map pattern type to weight key"""
        mapping = {
            "efficiency": "situational_stats",
            "conversion_rate": "historical_trends",
            "red_zone": "situational_stats",
            "two_minute": "live_odds_delta"
        }
        return mapping.get(pattern_type, "situational_stats")
```

---

## Phase 5: API Endpoints

### 5.1 Games Endpoint
**File:** `backend/app/api/games.py`

```python
from fastapi import APIRouter, Depends
from typing import List
from ..models.nfl_game import NFLGame
from ..services.espn_service import ESPNService

router = APIRouter()

@router.get("/games/live", response_model=List[NFLGame])
async def get_live_games(espn: ESPNService = Depends()):
    """Get all live NFL games"""
    return espn.get_live_games()

@router.get("/games/{game_id}", response_model=NFLGame)
async def get_game(game_id: str, espn: ESPNService = Depends()):
    """Get specific game by ID"""
    return espn.get_game(game_id)
```

### 5.2 Patterns Endpoint
**File:** `backend/app/api/patterns.py`

```python
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from ..models.third_down_pattern import ThirdDownPattern
from ..pattern_engines.third_down_analyzer import ThirdDownAnalyzer
from ..services.parser_client import ParserClient
from ..services.pattern_weighter import PatternWeighter

router = APIRouter()

@router.get("/patterns/{game_id}", response_model=List[ThirdDownPattern])
async def get_patterns(
    game_id: str,
    user_id: Optional[str] = Query(None),
    analyzer: ThirdDownAnalyzer = Depends(),
    parser: ParserClient = Depends(),
    weighter: PatternWeighter = Depends()
):
    """
    Get third down patterns for a game.
    If user_id provided, patterns are persona-weighted.
    """
    
    # Detect patterns
    patterns = analyzer.analyze_game(game_id)
    
    # Apply persona weights if user authenticated
    if user_id:
        persona = parser.get_user_persona(user_id)
        if persona:
            patterns = weighter.apply_weights(
                patterns, 
                persona["pattern_weights"]
            )
    
    return patterns
```

### 5.3 Odds Endpoint
**File:** `backend/app/api/odds.py`

```python
from fastapi import APIRouter, Depends
from typing import List
from ..models.game_odds import GameOdds
from ..services.odds_service import OddsAPIService

router = APIRouter()

@router.get("/odds/nfl", response_model=List[GameOdds])
async def get_nfl_odds(odds_api: OddsAPIService = Depends()):
    """Get current NFL betting odds"""
    return odds_api.get_nfl_odds()

@router.get("/odds/{game_id}/movement")
async def get_line_movement(game_id: str):
    """
    Get historical line movement for sharp money detection.
    Returns: Timestamp series of spread/total changes
    """
    # Query database for historical odds snapshots
    # Detect sharp money (rapid line moves opposite public)
    pass
```

---

## Phase 6: Background Workers

### 6.1 Odds Tracker Worker
**File:** `backend/app/workers/odds_tracker.py`

```python
import asyncio
from ..services.odds_service import OddsAPIService
from ..models.game_odds import GameOdds

class OddsTracker:
    """
    Background worker to track odds every 30 seconds.
    Why: Detect line movement in real-time.
    """
    
    def __init__(self, odds_api: OddsAPIService, db):
        self.odds_api = odds_api
        self.db = db
    
    async def run(self):
        """Main loop - runs every 30 seconds"""
        while True:
            try:
                # Fetch latest odds
                current_odds = self.odds_api.get_nfl_odds()
                
                # Store snapshot
                await self._store_odds(current_odds)
                
                # Detect sharp money
                alerts = await self._detect_sharp_money(current_odds)
                
                # Broadcast alerts via WebSocket
                if alerts:
                    await self._broadcast_alerts(alerts)
                
            except Exception as e:
                print(f"Odds tracker error: {e}")
            
            await asyncio.sleep(30)  # 30 seconds
    
    async def _detect_sharp_money(self, current_odds: List[GameOdds]):
        """
        Detect rapid line movement opposite public betting.
        Sharp money = Line moves toward team getting <50% of bets
        """
        alerts = []
        
        for odds in current_odds:
            # Get previous snapshot (30 seconds ago)
            prev_odds = await self.db.get_previous_odds(odds.game_id, odds.sportsbook)
            
            if not prev_odds:
                continue
            
            # Check spread movement
            spread_move = odds.home_spread - prev_odds.home_spread
            
            if abs(spread_move) >= 0.5:  # Moved half point or more
                # Check if opposite public (would need public betting %)
                # For now, flag any rapid movement
                alerts.append({
                    "type": "sharp_money",
                    "game_id": odds.game_id,
                    "sportsbook": odds.sportsbook,
                    "movement": float(spread_move),
                    "timestamp": odds.timestamp
                })
        
        return alerts
```

---

## Phase 7: Frontend (React)

### 7.1 Live Games View
**File:** `frontend/src/pages/LiveGames.jsx`

```jsx
import React, { useEffect, useState } from 'react';
import { useQuery } from 'react-query';

function LiveGames() {
  const { data: games, isLoading } = useQuery(
    'liveGames',
    () => fetch('/api/games/live').then(r => r.json()),
    { refetchInterval: 10000 } // Refresh every 10 seconds
  );
  
  if (isLoading) return <div>Loading live games...</div>;
  
  return (
    <div className="live-games">
      <h1>Live NFL Games</h1>
      {games.map(game => (
        <GameCard key={game.game_id} game={game} />
      ))}
    </div>
  );
}

function GameCard({ game }) {
  const { data: patterns } = useQuery(
    ['patterns', game.game_id],
    () => fetch(`/api/patterns/${game.game_id}?user_id=USER_ID`).then(r => r.json())
  );
  
  return (
    <div className="game-card">
      <div className="score">
        <span>{game.away_team} {game.away_score}</span>
        <span>@</span>
        <span>{game.home_team} {game.home_score}</span>
      </div>
      
      <div className="situation">
        {game.down && (
          <span>{game.down} & {game.distance} at {game.yard_line}</span>
        )}
      </div>
      
      {patterns && patterns.length > 0 && (
        <div className="patterns">
          <h3>🎯 Third Down Patterns</h3>
          {patterns.map((p, i) => (
            <PatternAlert key={i} pattern={p} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 7.2 Pattern Alert Component
**File:** `frontend/src/components/PatternAlert.jsx`

```jsx
function PatternAlert({ pattern }) {
  // Different styling based on persona weight
  const confidenceClass = 
    pattern.confidence_score > 0.8 ? 'high' :
    pattern.confidence_score > 0.5 ? 'medium' : 'low';
  
  return (
    <div className={`pattern-alert ${confidenceClass}`}>
      <div className="team">{pattern.team}</div>
      <div className="metric">
        {pattern.conversion_rate}% conversion rate
        ({pattern.variance_from_avg > 0 ? '+' : ''}{pattern.variance_from_avg}% vs avg)
      </div>
      <div className="context">
        {pattern.attempts} attempts • {pattern.distance_range} distance
      </div>
      {pattern.weight_applied > 1.2 && (
        <div className="persona-boost">
          ⭐ Boosted for your profile
        </div>
      )}
    </div>
  );
}
```

---

## Phase 8: Database Schema

**Tables:**

```sql
CREATE TABLE nfl_games (
    game_id VARCHAR PRIMARY KEY,
    home_team VARCHAR NOT NULL,
    away_team VARCHAR NOT NULL,
    start_time TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    quarter INTEGER,
    time_remaining VARCHAR,
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    possession VARCHAR,
    down INTEGER,
    distance INTEGER,
    yard_line INTEGER,
    week INTEGER NOT NULL,
    season INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE game_odds (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR NOT NULL,
    sportsbook VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    home_spread DECIMAL(4,1),
    home_spread_odds INTEGER,
    away_spread DECIMAL(4,1),
    away_spread_odds INTEGER,
    total DECIMAL(4,1),
    over_odds INTEGER,
    under_odds INTEGER,
    home_ml INTEGER,
    away_ml INTEGER,
    FOREIGN KEY (game_id) REFERENCES nfl_games(game_id)
);

CREATE INDEX idx_odds_game_time ON game_odds(game_id, timestamp DESC);

CREATE TABLE detected_patterns (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR NOT NULL,
    team VARCHAR NOT NULL,
    pattern_type VARCHAR NOT NULL,
    attempts INTEGER,
    conversions INTEGER,
    conversion_rate DECIMAL(4,3),
    distance_range VARCHAR,
    field_position VARCHAR,
    variance_from_avg DECIMAL(5,2),
    confidence_score DECIMAL(3,2),
    detected_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (game_id) REFERENCES nfl_games(game_id)
);
```

---

## Phase 9: WebSocket Real-Time Updates

**File:** `backend/app/websockets/game_updates.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

class GameUpdatesManager:
    """
    Manage WebSocket connections for real-time game updates.
    Why: Push pattern alerts and line movement to frontend instantly.
    """
    
    def __init__(self):
        # game_id -> set of connected clients
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, game_id: str):
        """Client subscribes to game updates"""
        await websocket.accept()
        
        if game_id not in self.active_connections:
            self.active_connections[game_id] = set()
        
        self.active_connections[game_id].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, game_id: str):
        """Client unsubscribes"""
        if game_id in self.active_connections:
            self.active_connections[game_id].discard(websocket)
    
    async def broadcast_pattern(self, game_id: str, pattern: dict):
        """Send pattern alert to all clients watching this game"""
        if game_id not in self.active_connections:
            return
        
        message = json.dumps({
            "type": "pattern_detected",
            "data": pattern
        })
        
        for connection in self.active_connections[game_id]:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                await self.disconnect(connection, game_id)
```

---

## Phase 10: Testing

### 10.1 Unit Tests
**File:** `backend/tests/test_third_down_analyzer.py`

```python
import pytest
from decimal import Decimal
from app.pattern_engines.third_down_analyzer import ThirdDownAnalyzer

def test_detect_high_efficiency():
    """Team converting >50% should trigger pattern"""
    analyzer = ThirdDownAnalyzer()
    
    data = {
        "third_down_attempts": 10,
        "third_down_conversions": 6,  # 60% (league avg 41%)
    }
    
    pattern = analyzer._analyze_team("game123", "KC", data)
    
    assert pattern is not None
    assert pattern.conversion_rate == Decimal("0.6")
    assert pattern.variance_from_avg > Decimal("10")

def test_ignore_small_variance():
    """<10% variance should not trigger pattern"""
    analyzer = ThirdDownAnalyzer()
    
    data = {
        "third_down_attempts": 10,
        "third_down_conversions": 4,  # 40% (league avg 41%)
    }
    
    pattern = analyzer._analyze_team("game123", "KC", data)
    
    assert pattern is None  # Variance too small
```

### 10.2 Integration Tests
**File:** `backend/tests/test_api_integration.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_live_games():
    """GET /games/live returns current games"""
    response = client.get("/api/games/live")
    
    assert response.status_code == 200
    games = response.json()
    assert isinstance(games, list)

def test_get_patterns_with_persona():
    """Patterns weighted by user persona"""
    response = client.get("/api/patterns/game123?user_id=user456")
    
    assert response.status_code == 200
    patterns = response.json()
    
    # Check patterns are weighted
    if patterns:
        assert "weight_applied" in patterns[0]
```

---

## Phase 11: Deployment

### 11.1 Railway Configuration
**File:** `railway.json`

```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### 11.2 Environment Variables (Railway)
```bash
DATABASE_URL=postgresql://...
PARSER_API_URL=https://parser-api.railway.app
ODDS_API_KEY=your_odds_api_key
LOG_LEVEL=INFO
CORS_ORIGINS=https://thirddowniq.vercel.app
```

### 11.3 Vercel Configuration
**File:** `frontend/vercel.json`

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "env": {
    "VITE_API_URL": "https://thirddowniq-api.railway.app"
  }
}
```

---

## Success Criteria

**Functional:**
- ✅ Fetches live NFL games from ESPN
- ✅ Ingests odds from The Odds API
- ✅ Detects third down patterns
- ✅ Applies persona weights to patterns
- ✅ WebSocket updates work in real-time
- ✅ Frontend displays personalized insights

**Performance:**
- ✅ API response time <100ms
- ✅ Pattern detection <50ms per game
- ✅ Odds updates every 30 seconds
- ✅ Game updates every 10 seconds

**Integration:**
- ✅ Calls DFS Parser API successfully
- ✅ Handles missing persona gracefully
- ✅ Database persists odds history
- ✅ WebSocket broadcasts to multiple clients

---

## Build Order for Claude Code

**Night 1:** Models + Services (Phases 1-2)
**Night 2:** Pattern Engine + Persona Integration (Phases 3-4)
**Night 3:** API Endpoints + Workers (Phases 5-6)
**Night 4:** Frontend + WebSocket (Phases 7-9)
**Night 5:** Testing + Deployment (Phases 10-11)

---

**Ready for autonomous execution. Clone this for ShotClockIQ (NBA) and PowerPlayIQ (NHL) after validation.**
