# ThirdDownIQ Magic Layer - Competitive Moat Features

## Overview
**Purpose:** Premium features that justify $29.99/month subscription and create competitive moat.

**Core Features:**
1. Social Proof - User activity tracking ("487 watching this line")
2. Smart Watchlist - Save props, get alerts on line movement
3. Active Bets Tracker - Track your bets, see live status
4. Prop Correlation Engine - Warn about correlated bets
5. Advanced Pattern Engines - Red zone, two-minute drill patterns

**Built on top of:** ThirdDownIQ v2 Core (02-THIRDDOWNIQ-V2-SPEC.md)

---

## Phase 1: User Activity Tracking (Social Proof)

### 1.1 Activity Model
**File:** `backend/app/models/user_activity.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Literal

class UserActivity(BaseModel):
    """
    Track user interactions for social proof aggregation.
    Why: "487 users watching this line" builds confidence.
    """
    user_id: str
    activity_type: Literal["view_pattern", "add_watchlist", "place_bet", "view_odds"]
    target_id: str  # game_id, prop_id, etc.
    target_type: Literal["game", "prop", "team", "line"]
    timestamp: datetime
    
    # Metadata
    metadata: dict = {}  # e.g., {"sportsbook": "draftkings", "line": "-3"}
```

### 1.2 Activity Tracker Service
**File:** `backend/app/services/activity_tracker.py`

```python
from datetime import datetime, timedelta
from typing import Dict
from ..models.user_activity import UserActivity

class ActivityTracker:
    """
    Aggregate user activity for social proof.
    Why: Show what other users are doing in real-time.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def track_activity(self, activity: UserActivity):
        """Log user activity"""
        await self.db.insert_activity(activity)
    
    async def get_watching_count(self, target_id: str, target_type: str) -> int:
        """
        Count unique users who viewed this in last hour.
        Returns: Number of active viewers
        """
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        count = await self.db.count_unique_users(
            target_id=target_id,
            target_type=target_type,
            activity_type="view_pattern",
            since=one_hour_ago
        )
        
        return count
    
    async def get_watchlist_count(self, target_id: str) -> int:
        """
        Count users who added this to watchlist today.
        Returns: Number of users tracking this
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0)
        
        count = await self.db.count_unique_users(
            target_id=target_id,
            activity_type="add_watchlist",
            since=today
        )
        
        return count
    
    async def get_betting_percentage(self, game_id: str, team: str) -> float:
        """
        Percentage of our users betting on this team.
        Returns: 0.0 to 1.0
        """
        total_bets = await self.db.count_bets_on_game(game_id)
        
        if total_bets == 0:
            return 0.0
        
        team_bets = await self.db.count_bets_on_team(game_id, team)
        
        return team_bets / total_bets
    
    async def get_trending_score(self, target_id: str) -> float:
        """
        Calculate trending score based on recent activity spike.
        Returns: Multiplier (1.0 = normal, 3.0 = 3x normal activity)
        """
        # Compare last hour to previous 24 hours
        last_hour = datetime.utcnow() - timedelta(hours=1)
        last_day = datetime.utcnow() - timedelta(days=1)
        
        recent_count = await self.db.count_activities(
            target_id=target_id,
            since=last_hour
        )
        
        baseline_count = await self.db.count_activities(
            target_id=target_id,
            since=last_day
        ) / 24  # Avg per hour
        
        if baseline_count == 0:
            return 1.0
        
        return recent_count / baseline_count
```

### 1.3 Social Proof API Endpoint
**File:** `backend/app/api/social.py`

```python
from fastapi import APIRouter, Depends
from ..services.activity_tracker import ActivityTracker

router = APIRouter()

@router.get("/social/{game_id}/stats")
async def get_social_stats(
    game_id: str,
    tracker: ActivityTracker = Depends()
):
    """
    Get aggregated social proof for a game.
    Returns: Watching count, betting percentages, trending score
    """
    
    watching = await tracker.get_watching_count(game_id, "game")
    watchlist = await tracker.get_watchlist_count(game_id)
    trending = await tracker.get_trending_score(game_id)
    
    # Get betting split (home vs away)
    # (Would need to query bets table for actual teams)
    
    return {
        "game_id": game_id,
        "watching_now": watching,
        "on_watchlist": watchlist,
        "trending_multiplier": trending,
        "user_distribution": {
            "home_bets_pct": 0.65,  # Example: 65% on home team
            "away_bets_pct": 0.35
        }
    }

@router.post("/social/track")
async def track_activity(
    activity: UserActivity,
    tracker: ActivityTracker = Depends()
):
    """Log user activity for social proof"""
    await tracker.track_activity(activity)
    return {"status": "tracked"}
```

---

## Phase 2: Smart Watchlist

### 2.1 Watchlist Item Model
**File:** `backend/app/models/watchlist.py`

```python
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

class WatchlistItem(BaseModel):
    """
    Saved prop/line user is considering.
    Why: Organize betting research, get alerts on movement.
    """
    id: int
    user_id: str
    created_at: datetime
    
    # What they're watching
    item_type: Literal["spread", "total", "moneyline", "prop"]
    game_id: str
    team: Optional[str] = None
    
    # Line details
    line: Decimal  # -3.5, 47.5, etc.
    odds: int  # -110
    sportsbook: str
    
    # Alerts
    alert_on_movement: bool = True
    movement_threshold: Decimal = Decimal("0.5")  # Alert if moves 0.5 pts
    
    # Status
    converted_to_bet: bool = False
```

### 2.2 Watchlist Service
**File:** `backend/app/services/watchlist_service.py`

```python
from typing import List
from decimal import Decimal
from ..models.watchlist import WatchlistItem
from ..models.game_odds import GameOdds

class WatchlistService:
    """
    Manage user's watchlist and send alerts.
    Why: Core feature for prop tracking workflow.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def add_item(self, item: WatchlistItem) -> WatchlistItem:
        """Add item to watchlist"""
        item_id = await self.db.insert_watchlist_item(item)
        item.id = item_id
        return item
    
    async def get_user_watchlist(self, user_id: str) -> List[WatchlistItem]:
        """Get all items on user's watchlist"""
        return await self.db.get_watchlist_items(user_id)
    
    async def check_for_movements(self, user_id: str, current_odds: List[GameOdds]):
        """
        Compare current odds to watchlist items.
        Send alert if line moved beyond threshold.
        """
        watchlist = await self.get_user_watchlist(user_id)
        alerts = []
        
        for item in watchlist:
            # Find current odds for this game/sportsbook
            current = self._find_matching_odds(item, current_odds)
            
            if not current:
                continue
            
            # Check if line moved
            movement = self._calculate_movement(item, current)
            
            if abs(movement) >= item.movement_threshold:
                alerts.append({
                    "item_id": item.id,
                    "original_line": float(item.line),
                    "current_line": float(current.home_spread),  # Example
                    "movement": float(movement),
                    "message": f"Line moved {movement:+.1f} pts"
                })
        
        return alerts
    
    def _calculate_movement(self, item: WatchlistItem, current: GameOdds) -> Decimal:
        """Calculate line movement"""
        if item.item_type == "spread":
            return current.home_spread - item.line
        elif item.item_type == "total":
            return current.total - item.line
        # ... handle other types
        return Decimal("0")
```

### 2.3 Watchlist API
**File:** `backend/app/api/watchlist.py`

```python
from fastapi import APIRouter, Depends, Query
from typing import List
from ..models.watchlist import WatchlistItem
from ..services.watchlist_service import WatchlistService

router = APIRouter()

@router.post("/watchlist", response_model=WatchlistItem)
async def add_to_watchlist(
    item: WatchlistItem,
    service: WatchlistService = Depends()
):
    """Add item to user's watchlist"""
    return await service.add_item(item)

@router.get("/watchlist", response_model=List[WatchlistItem])
async def get_watchlist(
    user_id: str = Query(...),
    service: WatchlistService = Depends()
):
    """Get user's watchlist"""
    return await service.get_user_watchlist(user_id)

@router.delete("/watchlist/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    service: WatchlistService = Depends()
):
    """Remove item from watchlist"""
    await service.delete_item(item_id)
    return {"status": "deleted"}

@router.get("/watchlist/alerts")
async def check_watchlist_alerts(
    user_id: str = Query(...),
    service: WatchlistService = Depends()
):
    """Check for line movement alerts"""
    # This would be called by frontend or background worker
    alerts = await service.check_for_movements(user_id)
    return {"alerts": alerts}
```

---

## Phase 3: Active Bets Tracker

### 3.1 Bet Model
**File:** `backend/app/models/bet.py`

```python
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

class Bet(BaseModel):
    """
    User's placed bet tracking.
    Why: Track performance, see live status during games.
    """
    id: int
    user_id: str
    placed_at: datetime
    
    # Bet details
    bet_type: Literal["spread", "total", "moneyline", "prop"]
    game_id: str
    team: Optional[str] = None
    player: Optional[str] = None
    
    # Line locked in
    line: Decimal
    odds: int  # American odds
    stake: Decimal
    to_win: Decimal
    
    # Status
    status: Literal["pending", "live", "won", "lost", "push"]
    result: Optional[Decimal] = None  # Actual outcome
    settled_at: Optional[datetime] = None
    
    # Metadata
    sportsbook: str
    notes: Optional[str] = None
```

### 3.2 Bet Tracker Service
**File:** `backend/app/services/bet_tracker.py`

```python
from typing import List
from decimal import Decimal
from datetime import datetime
from ..models.bet import Bet
from ..models.nfl_game import NFLGame

class BetTracker:
    """
    Track user bets and auto-grade when games finish.
    Why: Show ROI, win rate, performance stats.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def add_bet(self, bet: Bet) -> Bet:
        """Add bet to tracker"""
        bet_id = await self.db.insert_bet(bet)
        bet.id = bet_id
        return bet
    
    async def get_active_bets(self, user_id: str) -> List[Bet]:
        """Get bets that are pending or live"""
        return await self.db.get_bets(
            user_id=user_id,
            status=["pending", "live"]
        )
    
    async def update_bet_status(self, game: NFLGame):
        """
        Check all bets on this game, update status.
        If game is live, mark bets as "live".
        If game is final, grade bets as won/lost/push.
        """
        bets = await self.db.get_bets_by_game(game.game_id)
        
        for bet in bets:
            if game.status == "live":
                bet.status = "live"
            
            elif game.status == "final":
                # Grade the bet
                result = self._grade_bet(bet, game)
                bet.status = result
                bet.settled_at = datetime.utcnow()
            
            await self.db.update_bet(bet)
    
    def _grade_bet(self, bet: Bet, game: NFLGame) -> str:
        """
        Determine if bet won, lost, or pushed.
        Returns: "won", "lost", or "push"
        """
        if bet.bet_type == "spread":
            # Example: User bet Chiefs -3.5
            # Chiefs won 27-24, cover by 0.5
            # (Implementation would check actual spread result)
            pass
        
        # ... handle totals, ML, props
        
        return "won"  # Placeholder
    
    async def get_user_stats(self, user_id: str) -> dict:
        """
        Calculate user's betting performance.
        Returns: Win rate, ROI, total profit
        """
        all_bets = await self.db.get_bets(
            user_id=user_id,
            status=["won", "lost", "push"]
        )
        
        total_bets = len(all_bets)
        wins = len([b for b in all_bets if b.status == "won"])
        total_staked = sum(b.stake for b in all_bets)
        total_returned = sum(b.to_win for b in all_bets if b.status == "won")
        
        profit = total_returned - total_staked
        roi = (profit / total_staked * 100) if total_staked > 0 else 0
        
        return {
            "total_bets": total_bets,
            "wins": wins,
            "losses": total_bets - wins,
            "win_rate": wins / total_bets if total_bets > 0 else 0,
            "total_staked": float(total_staked),
            "total_profit": float(profit),
            "roi_pct": float(roi)
        }
```

### 3.3 Bets API
**File:** `backend/app/api/bets.py`

```python
from fastapi import APIRouter, Depends, Query
from typing import List
from ..models.bet import Bet
from ..services.bet_tracker import BetTracker

router = APIRouter()

@router.post("/bets", response_model=Bet)
async def add_bet(
    bet: Bet,
    tracker: BetTracker = Depends()
):
    """Add bet to tracker"""
    return await tracker.add_bet(bet)

@router.get("/bets/active", response_model=List[Bet])
async def get_active_bets(
    user_id: str = Query(...),
    tracker: BetTracker = Depends()
):
    """Get user's active bets"""
    return await tracker.get_active_bets(user_id)

@router.get("/bets/stats")
async def get_betting_stats(
    user_id: str = Query(...),
    tracker: BetTracker = Depends()
):
    """Get user's betting performance stats"""
    return await tracker.get_user_stats(user_id)

@router.patch("/bets/{bet_id}")
async def update_bet(
    bet_id: int,
    updates: dict,
    tracker: BetTracker = Depends()
):
    """Update bet (e.g., mark as won manually)"""
    await tracker.update_bet_manual(bet_id, updates)
    return {"status": "updated"}
```

---

## Phase 4: Prop Correlation Engine

### 4.1 Correlation Calculator
**File:** `backend/app/services/correlation_engine.py`

```python
from typing import List, Dict
from decimal import Decimal
from ..models.bet import Bet

class CorrelationEngine:
    """
    Detect correlated bets to warn users.
    Why: Prevent 3-leg parlays with 0.9 correlation (illusion of value).
    """
    
    # Pre-calculated correlation matrix
    CORRELATIONS = {
        ("QB_passing_yards", "WR_receiving_yards"): 0.73,
        ("Team_total", "QB_passing_TDs"): 0.81,
        ("Spread", "Total"): 0.42,
        ("Player_TD", "Team_wins"): 0.65,
        # ... many more
    }
    
    def analyze_watchlist(self, items: List[WatchlistItem]) -> List[dict]:
        """
        Check watchlist for correlated props.
        Returns: List of correlation warnings
        """
        warnings = []
        
        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                correlation = self._get_correlation(item1, item2)
                
                if correlation > 0.7:  # High correlation threshold
                    warnings.append({
                        "item1_id": item1.id,
                        "item2_id": item2.id,
                        "correlation": correlation,
                        "warning": f"These bets are {correlation:.0%} correlated",
                        "risk": "Parlay has lower value than it appears"
                    })
        
        return warnings
    
    def _get_correlation(self, item1: WatchlistItem, item2: WatchlistItem) -> float:
        """
        Look up correlation between two props.
        Returns: 0.0 (independent) to 1.0 (perfectly correlated)
        """
        # Same game correlation
        if item1.game_id != item2.game_id:
            return 0.0  # Different games = independent
        
        # Lookup correlation matrix
        key = (item1.item_type, item2.item_type)
        
        return self.CORRELATIONS.get(key, 0.0)
    
    def calculate_parlay_true_odds(self, items: List[WatchlistItem]) -> dict:
        """
        Adjust parlay payout for correlation.
        Returns: True odds vs displayed odds
        """
        # Convert American odds to decimal
        decimal_odds = [self._american_to_decimal(item.odds) for item in items]
        
        # Naive parlay calculation (assumes independence)
        naive_parlay_odds = 1.0
        for odds in decimal_odds:
            naive_parlay_odds *= odds
        
        # Adjust for correlation
        avg_correlation = self._average_correlation(items)
        correlation_penalty = 1 - (avg_correlation * 0.3)  # Example formula
        
        true_parlay_odds = naive_parlay_odds * correlation_penalty
        
        return {
            "displayed_odds": naive_parlay_odds,
            "true_odds": true_parlay_odds,
            "value_loss_pct": (1 - correlation_penalty) * 100
        }
```

### 4.2 Correlation API
**File:** `backend/app/api/correlations.py`

```python
from fastapi import APIRouter, Depends, Query
from ..services.correlation_engine import CorrelationEngine

router = APIRouter()

@router.post("/correlations/check")
async def check_correlations(
    watchlist_items: List[WatchlistItem],
    engine: CorrelationEngine = Depends()
):
    """Check watchlist for correlated bets"""
    warnings = engine.analyze_watchlist(watchlist_items)
    return {"warnings": warnings}

@router.post("/correlations/parlay")
async def analyze_parlay(
    items: List[WatchlistItem],
    engine: CorrelationEngine = Depends()
):
    """Calculate true parlay odds adjusted for correlation"""
    analysis = engine.calculate_parlay_true_odds(items)
    return analysis
```

---

## Phase 5: Advanced Pattern Engines

### 5.1 Red Zone Pattern Analyzer
**File:** `backend/app/pattern_engines/red_zone_analyzer.py`

```python
from decimal import Decimal
from typing import List
from ..models.third_down_pattern import ThirdDownPattern

class RedZoneAnalyzer:
    """
    Detect red zone efficiency patterns.
    Why: Red zone performance predicts scoring, impacts totals.
    """
    
    LEAGUE_AVG_RZ_TD_PCT = Decimal("0.58")  # 58% TD rate in red zone
    
    def analyze_team(self, team: str, game_data: dict) -> ThirdDownPattern:
        """
        Analyze team's red zone touchdown efficiency.
        Returns: Pattern if variance > 10%
        """
        rz_attempts = game_data.get("red_zone_attempts", 0)
        rz_tds = game_data.get("red_zone_tds", 0)
        
        if rz_attempts < 3:  # Need minimum sample
            return None
        
        td_rate = Decimal(rz_tds) / Decimal(rz_attempts)
        variance = ((td_rate - self.LEAGUE_AVG_RZ_TD_PCT) / 
                   self.LEAGUE_AVG_RZ_TD_PCT) * 100
        
        if abs(variance) < Decimal("10"):
            return None
        
        return ThirdDownPattern(
            game_id=game_data["game_id"],
            team=team,
            pattern_type="red_zone",
            attempts=rz_attempts,
            conversions=rz_tds,
            conversion_rate=td_rate,
            distance_range="red_zone",
            field_position="red_zone",
            variance_from_avg=variance,
            confidence_score=self._calculate_confidence(rz_attempts),
            weight_applied=Decimal("1.0")
        )
```

### 5.2 Two-Minute Drill Analyzer
**File:** `backend/app/pattern_engines/two_minute_analyzer.py`

```python
from decimal import Decimal

class TwoMinuteAnalyzer:
    """
    Detect two-minute drill efficiency.
    Why: End-of-half scoring impacts live totals.
    """
    
    def analyze_team(self, team: str, game_data: dict) -> dict:
        """
        Analyze team's two-minute drill performance.
        Returns: Points per two-minute opportunity
        """
        two_min_opportunities = game_data.get("two_min_drives", 0)
        two_min_points = game_data.get("two_min_points", 0)
        
        if two_min_opportunities == 0:
            return None
        
        points_per_drive = Decimal(two_min_points) / Decimal(two_min_opportunities)
        
        # League average is ~2.1 points per two-minute opportunity
        league_avg = Decimal("2.1")
        variance = ((points_per_drive - league_avg) / league_avg) * 100
        
        return {
            "team": team,
            "points_per_two_min": float(points_per_drive),
            "variance_from_avg": float(variance),
            "insight": "Strong two-minute offense" if variance > 20 else "Average"
        }
```

---

## Phase 6: Frontend Components

### 6.1 Social Proof Display
**File:** `frontend/src/components/SocialProof.jsx`

```jsx
function SocialProof({ gameId }) {
  const { data: social } = useQuery(
    ['social', gameId],
    () => fetch(`/api/social/${gameId}/stats`).then(r => r.json()),
    { refetchInterval: 30000 }  // Update every 30 seconds
  );
  
  if (!social) return null;
  
  return (
    <div className="social-proof">
      <div className="stat">
        <span className="icon">👀</span>
        <span className="value">{social.watching_now}</span>
        <span className="label">watching now</span>
      </div>
      
      <div className="stat">
        <span className="icon">⭐</span>
        <span className="value">{social.on_watchlist}</span>
        <span className="label">on watchlists</span>
      </div>
      
      {social.trending_multiplier > 2.0 && (
        <div className="trending">
          🔥 Trending: {social.trending_multiplier.toFixed(1)}x normal activity
        </div>
      )}
      
      <div className="betting-split">
        <div className="bar">
          <div 
            className="home" 
            style={{ width: `${social.user_distribution.home_bets_pct * 100}%` }}
          >
            {(social.user_distribution.home_bets_pct * 100).toFixed(0)}%
          </div>
          <div className="away">
            {(social.user_distribution.away_bets_pct * 100).toFixed(0)}%
          </div>
        </div>
        <div className="label">Our users betting split</div>
      </div>
    </div>
  );
}
```

### 6.2 Watchlist Component
**File:** `frontend/src/components/Watchlist.jsx`

```jsx
function Watchlist({ userId }) {
  const { data: items, refetch } = useQuery(
    ['watchlist', userId],
    () => fetch(`/api/watchlist?user_id=${userId}`).then(r => r.json())
  );
  
  const { data: alerts } = useQuery(
    ['watchlist-alerts', userId],
    () => fetch(`/api/watchlist/alerts?user_id=${userId}`).then(r => r.json()),
    { refetchInterval: 30000 }
  );
  
  const addToWatchlist = async (item) => {
    await fetch('/api/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item)
    });
    refetch();
  };
  
  return (
    <div className="watchlist">
      <h2>Your Watchlist</h2>
      
      {alerts?.alerts?.length > 0 && (
        <div className="alerts">
          {alerts.alerts.map(alert => (
            <Alert key={alert.item_id} alert={alert} />
          ))}
        </div>
      )}
      
      <div className="items">
        {items?.map(item => (
          <WatchlistItem key={item.id} item={item} />
        ))}
      </div>
      
      {items?.length === 0 && (
        <div className="empty">
          No items on watchlist. Add props you're considering!
        </div>
      )}
    </div>
  );
}

function WatchlistItem({ item }) {
  return (
    <div className="watchlist-item">
      <div className="main">
        <span className="team">{item.team}</span>
        <span className="line">{item.line}</span>
        <span className="odds">({item.odds > 0 ? '+' : ''}{item.odds})</span>
      </div>
      <div className="meta">
        <span className="sportsbook">{item.sportsbook}</span>
        <span className="time">{formatTime(item.created_at)}</span>
      </div>
      <div className="actions">
        <button onClick={() => convertToBet(item)}>Place Bet</button>
        <button onClick={() => removeFromWatchlist(item.id)}>Remove</button>
      </div>
    </div>
  );
}
```

### 6.3 Active Bets Tracker
**File:** `frontend/src/components/ActiveBets.jsx`

```jsx
function ActiveBets({ userId }) {
  const { data: bets } = useQuery(
    ['active-bets', userId],
    () => fetch(`/api/bets/active?user_id=${userId}`).then(r => r.json()),
    { refetchInterval: 10000 }  // Update every 10 seconds during games
  );
  
  const { data: stats } = useQuery(
    ['bet-stats', userId],
    () => fetch(`/api/bets/stats?user_id=${userId}`).then(r => r.json())
  );
  
  return (
    <div className="active-bets">
      <div className="stats-header">
        <div className="stat">
          <label>Win Rate</label>
          <value>{(stats?.win_rate * 100).toFixed(1)}%</value>
        </div>
        <div className="stat">
          <label>ROI</label>
          <value className={stats?.roi_pct > 0 ? 'positive' : 'negative'}>
            {stats?.roi_pct > 0 ? '+' : ''}{stats?.roi_pct.toFixed(1)}%
          </value>
        </div>
        <div className="stat">
          <label>Profit</label>
          <value>${stats?.total_profit.toFixed(2)}</value>
        </div>
      </div>
      
      <h2>Today's Bets ({bets?.length || 0})</h2>
      
      <div className="bets-list">
        {bets?.map(bet => (
          <BetCard key={bet.id} bet={bet} />
        ))}
      </div>
    </div>
  );
}

function BetCard({ bet }) {
  const statusEmoji = {
    pending: '⏱️',
    live: '🔴',
    won: '✅',
    lost: '❌',
    push: '↩️'
  };
  
  return (
    <div className={`bet-card ${bet.status}`}>
      <div className="header">
        <span className="status">{statusEmoji[bet.status]}</span>
        <span className="type">{bet.bet_type}</span>
      </div>
      <div className="details">
        <span className="team">{bet.team}</span>
        <span className="line">{bet.line}</span>
        <span className="odds">({bet.odds > 0 ? '+' : ''}{bet.odds})</span>
      </div>
      <div className="stake">
        ${bet.stake} to win ${bet.to_win}
      </div>
      {bet.status === 'live' && (
        <div className="live-status">
          Game in progress...
        </div>
      )}
    </div>
  );
}
```

---

## Phase 7: Database Schema Additions

```sql
-- User activity tracking (social proof)
CREATE TABLE user_activities (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    activity_type VARCHAR NOT NULL,
    target_id VARCHAR NOT NULL,
    target_type VARCHAR NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    INDEX idx_activities_target (target_id, target_type, timestamp DESC),
    INDEX idx_activities_user (user_id, timestamp DESC)
);

-- Watchlist
CREATE TABLE watchlist_items (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    item_type VARCHAR NOT NULL,
    game_id VARCHAR NOT NULL,
    team VARCHAR,
    line DECIMAL(5,2),
    odds INTEGER,
    sportsbook VARCHAR NOT NULL,
    alert_on_movement BOOLEAN DEFAULT TRUE,
    movement_threshold DECIMAL(3,1) DEFAULT 0.5,
    converted_to_bet BOOLEAN DEFAULT FALSE,
    INDEX idx_watchlist_user (user_id, created_at DESC)
);

-- Bets tracking
CREATE TABLE bets (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    placed_at TIMESTAMP DEFAULT NOW(),
    bet_type VARCHAR NOT NULL,
    game_id VARCHAR NOT NULL,
    team VARCHAR,
    player VARCHAR,
    line DECIMAL(5,2),
    odds INTEGER,
    stake DECIMAL(8,2),
    to_win DECIMAL(8,2),
    status VARCHAR DEFAULT 'pending',
    result DECIMAL(5,2),
    settled_at TIMESTAMP,
    sportsbook VARCHAR NOT NULL,
    notes TEXT,
    INDEX idx_bets_user (user_id, placed_at DESC),
    INDEX idx_bets_game (game_id, status)
);
```

---

## Success Criteria

**Social Proof:**
- ✅ Track user views, watchlist adds, bets placed
- ✅ Aggregate counts update in real-time
- ✅ Trending score detects activity spikes
- ✅ Display "487 watching" on patterns

**Watchlist:**
- ✅ Users can add/remove items
- ✅ Alerts trigger on line movement >0.5 pts
- ✅ One-click convert to bet

**Bet Tracker:**
- ✅ Manual bet entry works
- ✅ Auto-grade bets when games finish
- ✅ Display win rate, ROI, profit

**Correlations:**
- ✅ Warn about >0.7 correlated props
- ✅ Calculate true parlay odds
- ✅ Show value loss percentage

**Advanced Patterns:**
- ✅ Red zone efficiency detected
- ✅ Two-minute drill scoring tracked
- ✅ Patterns weighted by persona

---

## Build Order

**Night 1:** Social Proof (Phase 1)
**Night 2:** Watchlist (Phase 2)
**Night 3:** Bet Tracker (Phase 3)
**Night 4:** Correlations (Phase 4)
**Night 5:** Advanced Patterns (Phase 5)
**Night 6:** Frontend Components (Phase 6)
**Night 7:** Testing + Polish

---

**These features justify $29.99/month and create competitive moat.**
