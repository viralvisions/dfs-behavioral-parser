# ThirdDownIQ v2 - Magic Layer Features (Addendum Spec)

## Overview

**Purpose:** Extend ThirdDownIQ v2 foundation with advanced features that create true competitive moat.

**Prerequisites:** 
- DFS Behavioral Parser (complete)
- ThirdDownIQ v2 Core (Phases 1-6 from main spec)

**This addendum adds:**
- Social proof intelligence (user activity tracking)
- Prop correlation engine
- Advanced watchlist/bet tracking system
- Multi-factor pattern scoring
- Historical backtesting
- Enhanced pattern engines

**Build Order:**
1. Complete DFS Parser + ThirdDownIQ Core first
2. Then build these features in phases 7-11

---

## Phase 7: Social Proof & User Activity Tracking

### Objective
Track aggregate user behavior to generate social proof signals and crowd intelligence.

### Files to Create

#### 7.1 `backend/app/models/user_activity.py`

**Purpose:** Track user interactions for social proof aggregation.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Boolean
from datetime import datetime
from uuid import UUID

from app.database import Base

class UserActivity(Base):
    """
    Privacy-safe user activity tracking.
    
    Why aggregate only:
    - No PII (user_id hashed)
    - Can't trace back to individual
    - GDPR compliant
    - Enables social proof without privacy violation
    """
    __tablename__ = 'user_activities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Anonymized user (hashed ID)
    user_hash = Column(String, nullable=False)  # Hash of user_id, not actual ID
    
    # Activity type
    activity_type = Column(String, nullable=False)  # 'watch', 'bet_placed', 'pattern_viewed'
    
    # Target (what they're interacting with)
    game_id = Column(String, nullable=False)
    pattern_id = Column(Integer, ForeignKey('detected_patterns.id'))
    
    # Bet details (if activity_type = 'bet_placed')
    bet_type = Column(String)  # 'spread', 'total', 'moneyline', 'prop'
    bet_side = Column(String)  # 'home', 'away', 'over', 'under'
    bet_amount_bucket = Column(String)  # 'small' (<$25), 'medium' ($25-100), 'large' (>$100)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes for fast aggregation
    __table_args__ = (
        Index('idx_activity_game_type', 'game_id', 'activity_type'),
        Index('idx_activity_pattern', 'pattern_id'),
        Index('idx_activity_created', 'created_at'),
    )
    
    @staticmethod
    def hash_user_id(user_id: UUID) -> str:
        """
        One-way hash of user ID for privacy.
        
        Why one-way:
        - Can aggregate by same user (hash is consistent)
        - Cannot reverse to find actual user
        - GDPR safe
        """
        import hashlib
        return hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
```

**Tests Required:**
- Test hash_user_id() produces consistent hashes
- Test hash is non-reversible
- Test activity creation
- Test indexing performance

**Acceptance Criteria:**
- [ ] User hashing works consistently
- [ ] Cannot reverse hash to user_id
- [ ] Indexes created for aggregation
- [ ] Activity types properly categorized

---

#### 7.2 `backend/app/services/social_proof_service.py`

**Purpose:** Aggregate user activity into social proof signals.

**Implementation Requirements:**
```python
from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy import func
from decimal import Decimal

from app.models.user_activity import UserActivity
from app.database import get_db_session

class SocialProofService:
    """
    Generate social proof signals from aggregate user activity.
    
    Privacy first:
    - All data anonymized
    - Only counts/percentages shown
    - No individual user data exposed
    """
    
    def get_game_social_proof(self, game_id: str) -> Dict:
        """
        Get social proof metrics for a game.
        
        Returns:
            {
                'watchers_count': 487,
                'bets_placed_count': 156,
                'trending_score': 3.4,  # Multiplier vs avg
                'bet_distribution': {
                    'spread_home': 68,  # Percentage
                    'spread_away': 32,
                    'over': 55,
                    'under': 45,
                },
                'crowd_sentiment': 'BULLISH_HOME',  # or BEARISH, NEUTRAL
            }
        """
        with get_db_session() as db:
            # Get last 24 hours of activity
            since = datetime.utcnow() - timedelta(hours=24)
            
            # Watchers (unique users watching)
            watchers = db.query(func.count(func.distinct(UserActivity.user_hash))).filter(
                UserActivity.game_id == game_id,
                UserActivity.activity_type == 'watch',
                UserActivity.created_at >= since
            ).scalar() or 0
            
            # Bets placed (unique bets, not users - one user can place multiple)
            bets_placed = db.query(func.count(UserActivity.id)).filter(
                UserActivity.game_id == game_id,
                UserActivity.activity_type == 'bet_placed',
                UserActivity.created_at >= since
            ).scalar() or 0
            
            # Trending score (compare to average)
            avg_bets_per_game = self._get_average_bets_per_game(db)
            trending_score = (bets_placed / avg_bets_per_game) if avg_bets_per_game > 0 else 1.0
            
            # Bet distribution
            bet_dist = self._get_bet_distribution(db, game_id, since)
            
            # Crowd sentiment
            sentiment = self._calculate_crowd_sentiment(bet_dist)
            
            return {
                'watchers_count': watchers,
                'bets_placed_count': bets_placed,
                'trending_score': round(trending_score, 1),
                'bet_distribution': bet_dist,
                'crowd_sentiment': sentiment,
                'last_updated': datetime.utcnow().isoformat(),
            }
    
    def _get_average_bets_per_game(self, db) -> float:
        """Calculate average bets per game (last 7 days)"""
        since = datetime.utcnow() - timedelta(days=7)
        
        total_bets = db.query(func.count(UserActivity.id)).filter(
            UserActivity.activity_type == 'bet_placed',
            UserActivity.created_at >= since
        ).scalar() or 0
        
        unique_games = db.query(func.count(func.distinct(UserActivity.game_id))).filter(
            UserActivity.activity_type == 'bet_placed',
            UserActivity.created_at >= since
        ).scalar() or 1
        
        return total_bets / unique_games
    
    def _get_bet_distribution(self, db, game_id: str, since: datetime) -> Dict:
        """
        Calculate percentage distribution of bets.
        
        Returns:
            {
                'spread_home': 68,
                'spread_away': 32,
                'over': 55,
                'under': 45,
            }
        """
        bets = db.query(
            UserActivity.bet_type,
            UserActivity.bet_side,
            func.count(UserActivity.id).label('count')
        ).filter(
            UserActivity.game_id == game_id,
            UserActivity.activity_type == 'bet_placed',
            UserActivity.created_at >= since
        ).group_by(
            UserActivity.bet_type,
            UserActivity.bet_side
        ).all()
        
        distribution = {}
        
        # Calculate totals by type
        spread_total = sum(b.count for b in bets if b.bet_type == 'spread')
        total_total = sum(b.count for b in bets if b.bet_type == 'total')
        
        for bet in bets:
            if bet.bet_type == 'spread' and spread_total > 0:
                key = f"spread_{bet.bet_side}"
                distribution[key] = round((bet.count / spread_total) * 100)
            elif bet.bet_type == 'total' and total_total > 0:
                key = bet.bet_side  # 'over' or 'under'
                distribution[key] = round((bet.count / total_total) * 100)
        
        return distribution
    
    def _calculate_crowd_sentiment(self, bet_dist: Dict) -> str:
        """
        Determine crowd sentiment from bet distribution.
        
        Returns:
            'BULLISH_HOME' | 'BEARISH_HOME' | 'BULLISH_OVER' | 'BEARISH_OVER' | 'NEUTRAL'
        """
        spread_home = bet_dist.get('spread_home', 0)
        spread_away = bet_dist.get('spread_away', 0)
        over_pct = bet_dist.get('over', 0)
        under_pct = bet_dist.get('under', 0)
        
        # Strong sentiment threshold: 65%+
        if spread_home >= 65:
            return 'BULLISH_HOME'
        elif spread_away >= 65:
            return 'BEARISH_HOME'
        elif over_pct >= 65:
            return 'BULLISH_OVER'
        elif under_pct >= 65:
            return 'BEARISH_OVER'
        else:
            return 'NEUTRAL'
    
    def get_pattern_social_proof(self, pattern_id: int) -> Dict:
        """
        Get social proof for specific pattern.
        
        Returns:
            {
                'views': 234,
                'bets_influenced': 45,  # Bets placed within 1hr of viewing pattern
                'conversion_rate': 0.19,  # 19% of viewers bet
            }
        """
        with get_db_session() as db:
            since = datetime.utcnow() - timedelta(hours=24)
            
            # Pattern views
            views = db.query(func.count(UserActivity.id)).filter(
                UserActivity.pattern_id == pattern_id,
                UserActivity.activity_type == 'pattern_viewed',
                UserActivity.created_at >= since
            ).scalar() or 0
            
            # Bets influenced (users who viewed pattern then bet within 1hr)
            # This is approximate - tracks same user_hash
            pattern_viewers = db.query(UserActivity.user_hash).filter(
                UserActivity.pattern_id == pattern_id,
                UserActivity.activity_type == 'pattern_viewed',
                UserActivity.created_at >= since
            ).distinct().all()
            
            viewer_hashes = [v[0] for v in pattern_viewers]
            
            if viewer_hashes:
                bets_influenced = db.query(func.count(UserActivity.id)).filter(
                    UserActivity.user_hash.in_(viewer_hashes),
                    UserActivity.activity_type == 'bet_placed',
                    UserActivity.created_at >= since
                ).scalar() or 0
            else:
                bets_influenced = 0
            
            conversion = (bets_influenced / views) if views > 0 else 0
            
            return {
                'views': views,
                'bets_influenced': bets_influenced,
                'conversion_rate': round(conversion, 2),
            }
```

**Tests Required:**
- Test get_game_social_proof() aggregation
- Test bet distribution calculation
- Test crowd sentiment logic
- Test pattern social proof metrics
- Test privacy preservation (no PII exposed)

**Acceptance Criteria:**
- [ ] All metrics aggregate correctly
- [ ] No user PII in responses
- [ ] Trending score calculation works
- [ ] Sentiment detection accurate

---

#### 7.3 `backend/app/api/social_proof.py`

**Purpose:** API endpoints for social proof data.

**Implementation Requirements:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.social_proof_service import SocialProofService
from app.models.user_activity import UserActivity
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/social", tags=["social-proof"])

@router.get("/game/{game_id}")
def get_game_social_proof(game_id: str):
    """
    Get social proof metrics for a game.
    
    Public endpoint - no auth required (aggregate data only)
    """
    service = SocialProofService()
    return service.get_game_social_proof(game_id)

@router.get("/pattern/{pattern_id}")
def get_pattern_social_proof(pattern_id: int):
    """Get social proof for specific pattern"""
    service = SocialProofService()
    return service.get_pattern_social_proof(pattern_id)

@router.post("/track")
def track_user_activity(
    activity_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Track user activity for social proof.
    
    Body:
        {
            'activity_type': 'watch' | 'bet_placed' | 'pattern_viewed',
            'game_id': '2024_01_KC_DET',
            'pattern_id': 123,  # Optional
            'bet_type': 'spread',  # If bet_placed
            'bet_side': 'home',  # If bet_placed
            'bet_amount': 50,  # If bet_placed
        }
    """
    # Determine bet amount bucket (privacy)
    bet_amount = activity_data.get('bet_amount', 0)
    if bet_amount < 25:
        bucket = 'small'
    elif bet_amount < 100:
        bucket = 'medium'
    else:
        bucket = 'large'
    
    # Create activity record
    activity = UserActivity(
        user_hash=UserActivity.hash_user_id(user.id),
        activity_type=activity_data['activity_type'],
        game_id=activity_data['game_id'],
        pattern_id=activity_data.get('pattern_id'),
        bet_type=activity_data.get('bet_type'),
        bet_side=activity_data.get('bet_side'),
        bet_amount_bucket=bucket if activity_data['activity_type'] == 'bet_placed' else None,
    )
    
    db.add(activity)
    db.commit()
    
    return {"status": "tracked"}
```

**Tests Required:**
- Test game social proof endpoint
- Test pattern social proof endpoint
- Test activity tracking endpoint
- Test privacy preservation

**Acceptance Criteria:**
- [ ] Endpoints return correct data
- [ ] Activity tracking works
- [ ] User IDs properly hashed
- [ ] No auth required for read endpoints

---

### Phase 7 Checkpoint

**Before proceeding to Phase 8:**
- [ ] User activity tracking implemented
- [ ] Social proof aggregation working
- [ ] API endpoints functional
- [ ] Privacy compliance verified
- [ ] Frontend can display social proof

---

## Phase 8: Watchlist & Bet Tracking System

### Objective
Let users organize bets in staging area (watchlist) and track active bets.

### Files to Create

#### 8.1 `backend/app/models/watchlist.py`

**Purpose:** User's bet watchlist (staging area).

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, DECIMAL, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class WatchlistItem(Base):
    """
    User's bet watchlist - staging area before placing bet.
    
    Why separate from bets:
    - User can consider multiple options
    - Track what they're watching vs what they committed to
    - Auto-alerts when watched line moves
    """
    __tablename__ = 'watchlist_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Bet details
    game_id = Column(String, ForeignKey('nfl_games.game_id'), nullable=False)
    bet_type = Column(String, nullable=False)  # 'spread', 'total', 'moneyline', 'prop'
    bet_side = Column(String, nullable=False)  # 'home', 'away', 'over', 'under', etc.
    
    # Line when added
    line_when_added = Column(DECIMAL(5, 1))  # -3.5, 47.5, etc.
    odds_when_added = Column(Integer)  # -110, +150, etc.
    sportsbook = Column(String)  # 'draftkings', 'fanduel', etc.
    
    # Optional user notes
    notes = Column(String)  # "Waiting for line to move to -3"
    target_line = Column(DECIMAL(5, 1))  # Alert me when line hits this
    
    # Alert settings
    alert_on_movement = Column(Boolean, default=True)
    alert_threshold = Column(DECIMAL(3, 1), default=0.5)  # Alert if moves 0.5+ pts
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    game = relationship("NFLGame")
    
    def check_for_line_movement(self, current_line: float) -> bool:
        """
        Check if line has moved enough to alert user.
        
        Returns:
            True if alert should be sent
        """
        if not self.alert_on_movement or not self.line_when_added:
            return False
        
        movement = abs(current_line - float(self.line_when_added))
        return movement >= float(self.alert_threshold)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'game_id': self.game_id,
            'bet_type': self.bet_type,
            'bet_side': self.bet_side,
            'line_when_added': str(self.line_when_added) if self.line_when_added else None,
            'odds_when_added': self.odds_when_added,
            'sportsbook': self.sportsbook,
            'notes': self.notes,
            'target_line': str(self.target_line) if self.target_line else None,
            'created_at': self.created_at.isoformat(),
        }
```

**Tests Required:**
- Test watchlist item creation
- Test line movement detection
- Test alert threshold logic
- Test to_dict() serialization

**Acceptance Criteria:**
- [ ] Watchlist items store correctly
- [ ] Line movement alerts trigger properly
- [ ] User can set custom thresholds
- [ ] Serialization works

---

#### 8.2 `backend/app/models/bet.py`

**Purpose:** Track user's placed bets.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, DECIMAL, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.database import Base

class BetStatus(str, Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    PUSH = "push"
    VOID = "void"

class Bet(Base):
    """
    User's placed bets.
    
    Why track:
    - Performance analysis
    - Win/loss tracking
    - ROI calculation
    - Historical reference
    """
    __tablename__ = 'bets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Bet details
    game_id = Column(String, ForeignKey('nfl_games.game_id'), nullable=False)
    bet_type = Column(String, nullable=False)
    bet_side = Column(String, nullable=False)
    
    # Line details
    line = Column(DECIMAL(5, 1))
    odds = Column(Integer, nullable=False)
    sportsbook = Column(String, nullable=False)
    
    # Stake and payout
    stake = Column(DECIMAL(10, 2), nullable=False)  # Amount wagered
    to_win = Column(DECIMAL(10, 2), nullable=False)  # Potential win
    actual_payout = Column(DECIMAL(10, 2))  # Actual payout (if graded)
    
    # Status
    status = Column(String, default=BetStatus.PENDING)
    
    # Pattern that influenced this bet (optional)
    pattern_id = Column(Integer, ForeignKey('detected_patterns.id'))
    
    # User notes
    notes = Column(String)
    
    # Metadata
    placed_at = Column(DateTime, default=datetime.utcnow)
    graded_at = Column(DateTime)  # When result was determined
    
    # Relationships
    user = relationship("User")
    game = relationship("NFLGame")
    pattern = relationship("DetectedPattern")
    
    @property
    def profit(self) -> float:
        """Net profit/loss"""
        if self.status == BetStatus.WON:
            return float(self.to_win)
        elif self.status == BetStatus.LOST:
            return -float(self.stake)
        elif self.status == BetStatus.PUSH:
            return 0.0
        else:
            return 0.0  # Pending
    
    @property
    def roi(self) -> float:
        """Return on investment percentage"""
        if self.status == BetStatus.PENDING:
            return 0.0
        return (self.profit / float(self.stake)) * 100
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'game_id': self.game_id,
            'bet_type': self.bet_type,
            'bet_side': self.bet_side,
            'line': str(self.line) if self.line else None,
            'odds': self.odds,
            'sportsbook': self.sportsbook,
            'stake': str(self.stake),
            'to_win': str(self.to_win),
            'status': self.status,
            'profit': self.profit,
            'roi': round(self.roi, 2),
            'placed_at': self.placed_at.isoformat(),
            'graded_at': self.graded_at.isoformat() if self.graded_at else None,
        }
```

**Tests Required:**
- Test bet creation
- Test profit calculation
- Test ROI calculation
- Test status transitions
- Test to_dict() serialization

**Acceptance Criteria:**
- [ ] Bets store correctly
- [ ] Profit/ROI calculated accurately
- [ ] Status updates work
- [ ] Serialization works

---

#### 8.3 `backend/app/api/bets.py`

**Purpose:** API endpoints for watchlist and bet management.

**Implementation Requirements:**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.watchlist import WatchlistItem
from app.models.bet import Bet, BetStatus
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/bets", tags=["bets"])

# === Watchlist Endpoints ===

@router.get("/watchlist", response_model=List[dict])
def get_watchlist(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's watchlist"""
    items = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user.id
    ).order_by(WatchlistItem.created_at.desc()).all()
    
    return [item.to_dict() for item in items]

@router.post("/watchlist")
def add_to_watchlist(
    item_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add item to watchlist.
    
    Body:
        {
            'game_id': '2024_01_KC_DET',
            'bet_type': 'spread',
            'bet_side': 'home',
            'line_when_added': -3.5,
            'odds_when_added': -110,
            'sportsbook': 'draftkings',
            'notes': 'Waiting for -3',
            'target_line': -3.0,
        }
    """
    item = WatchlistItem(
        user_id=user.id,
        **item_data
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return item.to_dict()

@router.delete("/watchlist/{item_id}")
def remove_from_watchlist(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove item from watchlist"""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    
    return {"status": "deleted"}

@router.post("/watchlist/{item_id}/convert-to-bet")
def convert_watchlist_to_bet(
    item_id: int,
    bet_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Convert watchlist item to placed bet.
    
    Body:
        {
            'stake': 50.00,
            'odds': -110,  # Current odds (may differ from watchlist)
            'line': -3.0,  # Current line
        }
    """
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Calculate to_win based on odds
    stake = bet_data['stake']
    odds = bet_data['odds']
    
    if odds < 0:
        to_win = (stake / abs(odds)) * 100
    else:
        to_win = (stake / 100) * odds
    
    # Create bet
    bet = Bet(
        user_id=user.id,
        game_id=item.game_id,
        bet_type=item.bet_type,
        bet_side=item.bet_side,
        line=bet_data.get('line', item.line_when_added),
        odds=odds,
        sportsbook=item.sportsbook,
        stake=stake,
        to_win=to_win,
        status=BetStatus.PENDING,
    )
    
    db.add(bet)
    
    # Remove from watchlist
    db.delete(item)
    
    db.commit()
    db.refresh(bet)
    
    return bet.to_dict()

# === Bet Endpoints ===

@router.get("/", response_model=List[dict])
def get_bets(
    status: str = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's bets, optionally filtered by status"""
    query = db.query(Bet).filter(Bet.user_id == user.id)
    
    if status:
        query = query.filter(Bet.status == status)
    
    bets = query.order_by(Bet.placed_at.desc()).all()
    
    return [bet.to_dict() for bet in bets]

@router.post("/")
def place_bet(
    bet_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a placed bet.
    
    Body:
        {
            'game_id': '2024_01_KC_DET',
            'bet_type': 'spread',
            'bet_side': 'home',
            'line': -3.0,
            'odds': -110,
            'sportsbook': 'draftkings',
            'stake': 50.00,
            'pattern_id': 123,  # Optional
        }
    """
    stake = bet_data['stake']
    odds = bet_data['odds']
    
    # Calculate to_win
    if odds < 0:
        to_win = (stake / abs(odds)) * 100
    else:
        to_win = (stake / 100) * odds
    
    bet = Bet(
        user_id=user.id,
        to_win=to_win,
        **bet_data
    )
    
    db.add(bet)
    db.commit()
    db.refresh(bet)
    
    return bet.to_dict()

@router.patch("/{bet_id}/grade")
def grade_bet(
    bet_id: int,
    grade_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Grade a bet (mark as won/lost/push).
    
    Body:
        {
            'status': 'won' | 'lost' | 'push' | 'void'
        }
    """
    bet = db.query(Bet).filter(
        Bet.id == bet_id,
        Bet.user_id == user.id
    ).first()
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    bet.status = grade_data['status']
    bet.graded_at = datetime.utcnow()
    
    if bet.status == BetStatus.WON:
        bet.actual_payout = bet.stake + bet.to_win
    elif bet.status == BetStatus.PUSH:
        bet.actual_payout = bet.stake
    else:
        bet.actual_payout = 0
    
    db.commit()
    db.refresh(bet)
    
    return bet.to_dict()

@router.get("/stats")
def get_bet_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's betting statistics.
    
    Returns:
        {
            'total_bets': 156,
            'total_wagered': 5430.00,
            'total_won': 3890.00,
            'net_profit': -1540.00,
            'roi': -28.4,
            'win_rate': 0.42,
            'avg_stake': 34.81,
        }
    """
    from sqlalchemy import func
    
    bets = db.query(Bet).filter(
        Bet.user_id == user.id,
        Bet.status.in_([BetStatus.WON, BetStatus.LOST, BetStatus.PUSH])
    ).all()
    
    if not bets:
        return {
            'total_bets': 0,
            'total_wagered': 0,
            'total_won': 0,
            'net_profit': 0,
            'roi': 0,
            'win_rate': 0,
            'avg_stake': 0,
        }
    
    total_wagered = sum(float(b.stake) for b in bets)
    total_won = sum(b.profit for b in bets if b.status == BetStatus.WON)
    net_profit = sum(b.profit for b in bets)
    wins = sum(1 for b in bets if b.status == BetStatus.WON)
    
    return {
        'total_bets': len(bets),
        'total_wagered': round(total_wagered, 2),
        'total_won': round(total_won, 2),
        'net_profit': round(net_profit, 2),
        'roi': round((net_profit / total_wagered) * 100, 2) if total_wagered > 0 else 0,
        'win_rate': round(wins / len(bets), 2),
        'avg_stake': round(total_wagered / len(bets), 2),
    }
```

**Tests Required:**
- Test watchlist CRUD operations
- Test watchlist → bet conversion
- Test bet placement
- Test bet grading
- Test stats calculation

**Acceptance Criteria:**
- [ ] Watchlist management works
- [ ] Bet tracking works
- [ ] Conversion flow works
- [ ] Stats calculated correctly

---

### Phase 8 Checkpoint

**Before proceeding to Phase 9:**
- [ ] Watchlist system functional
- [ ] Bet tracking working
- [ ] Conversion flow tested
- [ ] Stats endpoints accurate
- [ ] Frontend can manage watchlist/bets

---

## Phase 9: Prop Correlation Engine

### Objective
Detect correlated bets to help users manage variance and build parlays.

### Files to Create

#### 9.1 `backend/app/services/correlation_service.py`

**Purpose:** Calculate prop correlations from historical data.

**Implementation Requirements:**
```python
from typing import List, Dict
from decimal import Decimal
import math

class CorrelationService:
    """
    Calculate correlations between props.
    
    Why this matters:
    - Parlaying correlated props = increased variance
    - Example: QB TDs + WR yards = highly correlated
    - Users should know when they're compounding risk
    """
    
    # Hardcoded correlation matrix (would be calculated from historical data in production)
    KNOWN_CORRELATIONS = {
        # QB props
        ('qb_passing_tds', 'qb_passing_yards'): 0.82,
        ('qb_passing_tds', 'team_total'): 0.75,
        
        # WR props
        ('wr_receiving_yards', 'qb_passing_yards'): 0.68,
        ('wr_receiving_tds', 'qb_passing_tds'): 0.71,
        
        # RB props
        ('rb_rushing_yards', 'team_total'): 0.54,
        ('rb_rushing_tds', 'team_total'): 0.63,
        
        # Spread/total correlations
        ('spread', 'total'): -0.15,  # Slightly negative
        ('team_total', 'spread'): 0.58,
    }
    
    def find_correlations(self, prop_list: List[Dict]) -> List[Dict]:
        """
        Find correlations between a list of props.
        
        Args:
            prop_list: [
                {'type': 'qb_passing_tds', 'player': 'Mahomes', 'line': 1.5},
                {'type': 'wr_receiving_yards', 'player': 'Kelce', 'line': 62.5},
            ]
            
        Returns:
            [
                {
                    'prop_1': 'Mahomes O1.5 TD',
                    'prop_2': 'Kelce O62.5 yards',
                    'correlation': 0.71,
                    'risk_level': 'HIGH',
                    'explanation': 'Kelce TDs require Mahomes TD passes',
                },
            ]
        """
        correlations = []
        
        for i, prop1 in enumerate(prop_list):
            for prop2 in prop_list[i+1:]:
                corr = self._calculate_correlation(prop1, prop2)
                
                if corr and abs(corr['correlation']) > 0.5:  # Only show strong correlations
                    correlations.append(corr)
        
        return sorted(correlations, key=lambda x: abs(x['correlation']), reverse=True)
    
    def _calculate_correlation(self, prop1: Dict, prop2: Dict) -> Dict:
        """Calculate correlation between two props"""
        
        # Check if same player
        if prop1.get('player') == prop2.get('player'):
            return {
                'prop_1': f"{prop1['player']} {prop1['type']}",
                'prop_2': f"{prop2['player']} {prop2['type']}",
                'correlation': 0.95,  # Same player props highly correlated
                'risk_level': 'EXTREME',
                'explanation': 'Same player - props are nearly perfectly correlated',
            }
        
        # Check known correlations
        key = (prop1['type'], prop2['type'])
        reverse_key = (prop2['type'], prop1['type'])
        
        corr_value = self.KNOWN_CORRELATIONS.get(key) or self.KNOWN_CORRELATIONS.get(reverse_key)
        
        if corr_value:
            risk_level = self._get_risk_level(corr_value)
            explanation = self._get_correlation_explanation(prop1['type'], prop2['type'])
            
            return {
                'prop_1': f"{prop1.get('player', prop1['type'])} {prop1['type']}",
                'prop_2': f"{prop2.get('player', prop2['type'])} {prop2['type']}",
                'correlation': corr_value,
                'risk_level': risk_level,
                'explanation': explanation,
            }
        
        return None
    
    def _get_risk_level(self, correlation: float) -> str:
        """Convert correlation to risk level"""
        abs_corr = abs(correlation)
        
        if abs_corr > 0.8:
            return 'EXTREME'
        elif abs_corr > 0.6:
            return 'HIGH'
        elif abs_corr > 0.4:
            return 'MODERATE'
        else:
            return 'LOW'
    
    def _get_correlation_explanation(self, type1: str, type2: str) -> str:
        """Generate human-readable explanation"""
        explanations = {
            ('qb_passing_tds', 'wr_receiving_tds'): 'WR TDs require QB TD passes',
            ('qb_passing_yards', 'wr_receiving_yards'): 'WR yards contribute to QB yards',
            ('rb_rushing_yards', 'team_total'): 'RB success correlates with scoring',
            ('spread', 'team_total'): 'Blowouts affect total scoring',
        }
        
        key = (type1, type2)
        reverse = (type2, type1)
        
        return explanations.get(key) or explanations.get(reverse) or 'Props are statistically correlated'
    
    def calculate_parlay_variance(self, props: List[Dict]) -> Dict:
        """
        Calculate variance multiplier for parlaying correlated props.
        
        Returns:
            {
                'variance_multiplier': 2.3,
                'warning': 'HIGH',
                'recommendation': 'Consider reducing stake or removing correlated props',
            }
        """
        if len(props) < 2:
            return {'variance_multiplier': 1.0, 'warning': 'NONE'}
        
        correlations = self.find_correlations(props)
        
        # Calculate average correlation
        if correlations:
            avg_corr = sum(abs(c['correlation']) for c in correlations) / len(correlations)
        else:
            avg_corr = 0.1  # Assume slight correlation
        
        # Variance multiplier = 1 + (avg_correlation * number_of_legs)
        variance_mult = 1 + (avg_corr * (len(props) - 1))
        
        # Generate warning
        if variance_mult > 2.5:
            warning = 'EXTREME'
            rec = 'Highly correlated parlay - consider single bets instead'
        elif variance_mult > 1.8:
            warning = 'HIGH'
            rec = 'Consider reducing stake due to correlation'
        elif variance_mult > 1.3:
            warning = 'MODERATE'
            rec = 'Some correlation present - be aware of compounded risk'
        else:
            warning = 'LOW'
            rec = 'Props are relatively independent'
        
        return {
            'variance_multiplier': round(variance_mult, 2),
            'warning': warning,
            'recommendation': rec,
            'correlations': correlations,
        }
```

**Tests Required:**
- Test correlation detection
- Test same-player correlation
- Test risk level calculation
- Test variance multiplier
- Test explanation generation

**Acceptance Criteria:**
- [ ] Detects strong correlations (>0.5)
- [ ] Same player correlations flagged
- [ ] Variance multiplier accurate
- [ ] Warnings appropriate

---

#### 9.2 `backend/app/api/correlations.py`

**Purpose:** API endpoints for correlation analysis.

**Implementation Requirements:**
```python
from fastapi import APIRouter
from typing import List

from app.services.correlation_service import CorrelationService

router = APIRouter(prefix="/api/correlations", tags=["correlations"])

@router.post("/analyze")
def analyze_correlations(props: List[dict]):
    """
    Analyze correlations between props.
    
    Body:
        [
            {'type': 'qb_passing_tds', 'player': 'Mahomes', 'line': 1.5},
            {'type': 'wr_receiving_yards', 'player': 'Kelce', 'line': 62.5},
        ]
    """
    service = CorrelationService()
    return service.find_correlations(props)

@router.post("/parlay-variance")
def calculate_parlay_variance(props: List[dict]):
    """
    Calculate variance risk for parlaying props.
    
    Returns risk assessment and recommendations.
    """
    service = CorrelationService()
    return service.calculate_parlay_variance(props)
```

**Tests Required:**
- Test analyze endpoint
- Test parlay variance endpoint
- Test with various prop combinations

**Acceptance Criteria:**
- [ ] Endpoints return correct data
- [ ] Handles empty prop lists
- [ ] Warnings generated appropriately

---

### Phase 9 Checkpoint

**Before proceeding to Phase 10:**
- [ ] Correlation detection working
- [ ] Variance calculation accurate
- [ ] API endpoints functional
- [ ] Frontend can display correlations

---

## Phase 10: Advanced Pattern Engines

### Objective
Add more sophisticated pattern detection beyond third down.

### Files to Create

#### 10.1 `backend/app/pattern_engines/red_zone_engine.py`

**Purpose:** Detect red zone efficiency patterns.

**Implementation Requirements:**
```python
from typing import List
from decimal import Decimal

from app.pattern_engines.base_engine import BasePatternEngine
from app.models.game import NFLGame
from app.models.pattern import DetectedPattern, PatternType

class RedZoneEngine(BasePatternEngine):
    """
    Detect red zone scoring patterns.
    
    Key metrics:
    - TD% vs FG% in red zone
    - Red zone trips per game
    - Goal-to-go conversion rate
    """
    
    @property
    def pattern_type(self) -> PatternType:
        return PatternType.RED_ZONE_EFFICIENCY
    
    def detect(self, game: NFLGame, historical_data: dict = None) -> List[DetectedPattern]:
        """
        Detect red zone patterns.
        
        Args:
            historical_data: {
                'team_rz_td_pct': {'KC': 0.65, 'DET': 0.58},
                'league_avg': 0.56,
                'rz_trips_per_game': {'KC': 4.2, 'DET': 3.8},
            }
        """
        patterns = []
        
        if not game.is_red_zone or not historical_data:
            return patterns
        
        possession_team = game.possession
        team_td_pct = historical_data.get('team_rz_td_pct', {}).get(possession_team, 0.56)
        league_avg = historical_data.get('league_avg', 0.56)
        
        edge = team_td_pct - league_avg
        
        if abs(edge) > 0.10:  # 10%+ edge
            base_score = min(abs(edge) / 0.25, Decimal('1.0'))
            
            direction = "above" if edge > 0 else "below"
            
            title = f"{possession_team} Red Zone TD%: {team_td_pct:.1%}"
            description = f"{possession_team} scores TDs {team_td_pct:.1%} in red zone, {abs(edge):.1%} {direction} league average"
            
            bettor_insight = f"Red zone advantage suggests {possession_team} {'Team Total Over' if edge > 0 else 'may struggle to convert'}."
            
            fantasy_insight = f"{possession_team} red zone weapons ({team_td_pct:.1%} TD rate) are strong plays near goal line."
            
            stats_insight = f"Red zone TD%: {team_td_pct:.1%} vs league {league_avg:.1%}. Field position: {game.yard_line} yard line."
            
            pattern = self.create_pattern(
                game_id=game.game_id,
                base_score=base_score,
                title=title,
                description=description,
                data={
                    'team': possession_team,
                    'rz_td_pct': team_td_pct,
                    'league_avg': league_avg,
                    'edge': edge,
                    'yard_line': game.yard_line,
                },
                bettor_insight=bettor_insight,
                fantasy_insight=fantasy_insight,
                stats_insight=stats_insight,
            )
            
            patterns.append(pattern)
        
        return patterns
```

**Tests Required:**
- Test pattern detection
- Test insight generation
- Test score calculation

**Acceptance Criteria:**
- [ ] Detects red zone patterns
- [ ] Generates persona insights
- [ ] Score scales appropriately

---

#### 10.2 `backend/app/pattern_engines/two_minute_drill_engine.py`

**Purpose:** Detect two-minute drill patterns.

**Implementation Requirements:**
```python
from typing import List
from decimal import Decimal

from app.pattern_engines.base_engine import BasePatternEngine
from app.models.game import NFLGame
from app.models.pattern import DetectedPattern, PatternType

class TwoMinuteDrillEngine(BasePatternEngine):
    """
    Detect two-minute drill efficiency.
    
    Key scenarios:
    - End of half scoring
    - Clock management
    - Aggressive vs conservative
    """
    
    @property
    def pattern_type(self) -> PatternType:
        return PatternType.SITUATIONAL_TREND
    
    def detect(self, game: NFLGame, historical_data: dict = None) -> List[DetectedPattern]:
        """Detect two-minute drill patterns"""
        patterns = []
        
        if not game.is_two_minute_drill or not historical_data:
            return patterns
        
        possession_team = game.possession
        team_2min_success = historical_data.get('two_min_success_rate', {}).get(possession_team, 0.45)
        league_avg = historical_data.get('league_avg', 0.45)
        
        edge = team_2min_success - league_avg
        
        if abs(edge) > 0.12:
            base_score = min(abs(edge) / 0.30, Decimal('1.0'))
            
            title = f"{possession_team} Two-Minute Drill Success: {team_2min_success:.1%}"
            description = f"{possession_team} scores in two-minute situations {team_2min_success:.1%} of time"
            
            bettor_insight = f"{'Consider live Over' if edge > 0 else 'Defense may hold'} - {possession_team} {team_2min_success:.1%} in 2-min drill."
            
            fantasy_insight = f"{possession_team} QB sees {historical_data.get('avg_2min_attempts', 8):.1f} pass attempts in 2-min drill. Target WRs."
            
            stats_insight = f"2-min success: {team_2min_success:.1%} vs {league_avg:.1%}. Time: {game.time_remaining}, Position: {game.yard_line}."
            
            pattern = self.create_pattern(
                game_id=game.game_id,
                base_score=base_score,
                title=title,
                description=description,
                data={
                    'team': possession_team,
                    'success_rate': team_2min_success,
                    'league_avg': league_avg,
                    'time_remaining': game.time_remaining,
                },
                bettor_insight=bettor_insight,
                fantasy_insight=fantasy_insight,
                stats_insight=stats_insight,
            )
            
            patterns.append(pattern)
        
        return patterns
```

**Tests Required:**
- Test pattern detection
- Test two-minute drill scenarios
- Test insight generation

**Acceptance Criteria:**
- [ ] Detects two-minute patterns
- [ ] Only triggers when < 2:00 remaining
- [ ] Generates appropriate insights

---

### Phase 10 Checkpoint

**Before final deployment:**
- [ ] Red zone engine working
- [ ] Two-minute drill engine working
- [ ] All pattern engines tested
- [ ] Pattern detection orchestration complete

---

## Phase 11: Frontend Integration

### Objective
Build UI components to surface all magic layer features.

### Files to Create

#### 11.1 `frontend/src/components/SocialProofBadge.tsx`

**Purpose:** Display social proof for game/pattern.

**Implementation Requirements:**
```typescript
import React from 'react';

interface SocialProofData {
  watchers_count: number;
  bets_placed_count: number;
  trending_score: number;
  crowd_sentiment: string;
}

interface Props {
  data: SocialProofData;
}

const SocialProofBadge: React.FC<Props> = ({ data }) => {
  const getTrendingIcon = () => {
    if (data.trending_score > 2.0) return '🔥';
    if (data.trending_score > 1.5) return '📈';
    return '👀';
  };
  
  const getSentimentColor = () => {
    switch (data.crowd_sentiment) {
      case 'BULLISH_HOME':
      case 'BULLISH_OVER':
        return 'text-green-600';
      case 'BEARISH_HOME':
      case 'BEARISH_OVER':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };
  
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-2xl">{getTrendingIcon()}</span>
      <div>
        <div className="font-semibold">
          {data.watchers_count.toLocaleString()} watching
        </div>
        <div className="text-gray-600">
          {data.bets_placed_count} bets placed
          {data.trending_score > 1.5 && (
            <span className="ml-2 text-orange-600 font-semibold">
              {data.trending_score}x trending
            </span>
          )}
        </div>
        <div className={`text-xs ${getSentimentColor()}`}>
          Crowd: {data.crowd_sentiment.replace('_', ' ')}
        </div>
      </div>
    </div>
  );
};

export default SocialProofBadge;
```

---

#### 11.2 `frontend/src/components/CorrelationWarning.tsx`

**Purpose:** Show correlation warnings for watchlist.

**Implementation Requirements:**
```typescript
import React from 'react';

interface Correlation {
  prop_1: string;
  prop_2: string;
  correlation: number;
  risk_level: string;
  explanation: string;
}

interface Props {
  correlations: Correlation[];
  variance_multiplier: number;
}

const CorrelationWarning: React.FC<Props> = ({ correlations, variance_multiplier }) => {
  if (correlations.length === 0) return null;
  
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'EXTREME': return 'bg-red-100 border-red-500 text-red-800';
      case 'HIGH': return 'bg-orange-100 border-orange-500 text-orange-800';
      case 'MODERATE': return 'bg-yellow-100 border-yellow-500 text-yellow-800';
      default: return 'bg-blue-100 border-blue-500 text-blue-800';
    }
  };
  
  return (
    <div className="border-2 rounded-lg p-4 mb-4 bg-yellow-50 border-yellow-400">
      <div className="flex items-start gap-2">
        <span className="text-2xl">⚠️</span>
        <div className="flex-1">
          <h4 className="font-bold text-lg mb-2">Correlation Detected</h4>
          <p className="text-sm mb-3">
            These bets are correlated. Variance multiplier: <strong>{variance_multiplier}x</strong>
          </p>
          
          {correlations.map((corr, idx) => (
            <div 
              key={idx}
              className={`border rounded p-2 mb-2 ${getRiskColor(corr.risk_level)}`}
            >
              <div className="font-semibold text-sm">
                {corr.prop_1} ↔ {corr.prop_2}
              </div>
              <div className="text-xs">
                Correlation: {(corr.correlation * 100).toFixed(0)}% | {corr.risk_level} RISK
              </div>
              <div className="text-xs mt-1 opacity-75">
                {corr.explanation}
              </div>
            </div>
          ))}
          
          <div className="mt-3 p-2 bg-white rounded border border-gray-300">
            <div className="text-sm font-semibold">💡 Recommendation</div>
            <div className="text-xs text-gray-700">
              {variance_multiplier > 2.5 
                ? 'Consider single bets instead of parlay'
                : variance_multiplier > 1.8
                ? 'Reduce stake size to account for correlation'
                : 'Be aware of compounded risk'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CorrelationWarning;
```

---

#### 11.3 `frontend/src/pages/Watchlist.tsx`

**Purpose:** Watchlist management page.

**Implementation Requirements:**
```typescript
import React, { useEffect, useState } from 'react';
import api from '../services/api';
import CorrelationWarning from '../components/CorrelationWarning';
import SocialProofBadge from '../components/SocialProofBadge';

interface WatchlistItem {
  id: number;
  game_id: string;
  bet_type: string;
  bet_side: string;
  line_when_added: number;
  odds_when_added: number;
  sportsbook: string;
  notes?: string;
}

const Watchlist: React.FC = () => {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [correlations, setCorrelations] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadWatchlist();
  }, []);
  
  useEffect(() => {
    if (items.length >= 2) {
      checkCorrelations();
    }
  }, [items]);
  
  const loadWatchlist = async () => {
    try {
      const response = await api.get('/bets/watchlist');
      setItems(response.data);
    } catch (error) {
      console.error('Error loading watchlist:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const checkCorrelations = async () => {
    try {
      const props = items.map(item => ({
        type: item.bet_type,
        player: item.bet_side,
        line: item.line_when_added,
      }));
      
      const response = await api.post('/correlations/parlay-variance', props);
      setCorrelations(response.data);
    } catch (error) {
      console.error('Error checking correlations:', error);
    }
  };
  
  const convertToBet = async (itemId: number) => {
    const stake = prompt('Enter stake amount:');
    if (!stake) return;
    
    try {
      await api.post(`/bets/watchlist/${itemId}/convert-to-bet`, {
        stake: parseFloat(stake),
        odds: items.find(i => i.id === itemId)?.odds_when_added,
        line: items.find(i => i.id === itemId)?.line_when_added,
      });
      
      await loadWatchlist();
      alert('Bet placed and removed from watchlist!');
    } catch (error) {
      console.error('Error converting to bet:', error);
      alert('Failed to place bet');
    }
  };
  
  const removeItem = async (itemId: number) => {
    try {
      await api.delete(`/bets/watchlist/${itemId}`);
      await loadWatchlist();
    } catch (error) {
      console.error('Error removing item:', error);
    }
  };
  
  if (loading) return <div className="p-8">Loading...</div>;
  
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Watchlist</h1>
      
      {correlations && correlations.correlations.length > 0 && (
        <CorrelationWarning 
          correlations={correlations.correlations}
          variance_multiplier={correlations.variance_multiplier}
        />
      )}
      
      {items.length === 0 && (
        <p className="text-gray-500">No items in watchlist</p>
      )}
      
      <div className="space-y-4">
        {items.map(item => (
          <div key={item.id} className="border rounded-lg p-4 bg-white">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-bold text-lg">
                  {item.game_id} - {item.bet_type} {item.bet_side}
                </h3>
                <p className="text-sm text-gray-600">
                  Line: {item.line_when_added} ({item.odds_when_added > 0 ? '+' : ''}{item.odds_when_added})
                </p>
                <p className="text-sm text-gray-500">
                  Sportsbook: {item.sportsbook}
                </p>
                {item.notes && (
                  <p className="text-sm italic mt-2">{item.notes}</p>
                )}
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={() => convertToBet(item.id)}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Place Bet
                </button>
                <button
                  onClick={() => removeItem(item.id)}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Remove
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Watchlist;
```

---

### Phase 11 Checkpoint

**Before launch:**
- [ ] Social proof badge displays
- [ ] Correlation warnings show
- [ ] Watchlist management works
- [ ] All UI components tested
- [ ] Mobile responsive

---

## Phase 12: Subscription Management & Stripe Integration

### Objective
Implement tiered subscription system with Stripe payment processing.

### Subscription Tiers

```
FREE
├── Persona profile from CSV upload
├── 3 patterns per week
└── Basic game info

SINGLE SPORT ($14.99/month or $119/year)
├── Choose: NFL, NBA, or NHL
├── Unlimited patterns for chosen sport
├── Real-time updates
├── Watchlist + bet tracking
├── Social proof
└── Correlation engine

ALL SPORTS ($29.99/month or $249/year)
├── Access all three sports
├── Everything in Single Sport
├── Cross-sport insights
└── Switch between sports

ELITE ($49.99/month or $399/year)
├── Everything in All Sports
├── Historical backtesting
├── API access
├── Advanced analytics
└── Priority support
```

### Files to Create

#### 12.1 `backend/app/models/subscription.py`

**Purpose:** Track user subscriptions and usage.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.database import Base

class SubscriptionTier(str, Enum):
    """Subscription tier levels"""
    FREE = "free"
    SINGLE_SPORT = "single_sport"
    ALL_SPORTS = "all_sports"
    ELITE = "elite"

class BillingInterval(str, Enum):
    """Billing frequency"""
    MONTHLY = "monthly"
    YEARLY = "yearly"

class Subscription(Base):
    """
    User subscription details.
    
    Why separate from User:
    - Clean separation of concerns
    - Track subscription history
    - Handle upgrades/downgrades
    - Stripe webhook updates
    """
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    
    # Subscription details
    tier = Column(String, nullable=False, default=SubscriptionTier.FREE)
    billing_interval = Column(String)  # monthly or yearly
    
    # Sport access (for SINGLE_SPORT tier)
    subscribed_sport = Column(String)  # "NFL", "NBA", "NHL"
    
    # Stripe integration
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    stripe_price_id = Column(String)  # Stripe price ID for current plan
    
    # Status
    is_active = Column(Boolean, default=False)
    is_trial = Column(Boolean, default=False)
    trial_ends_at = Column(DateTime)
    
    # Billing dates
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    @property
    def is_expired(self) -> bool:
        """Check if subscription has expired"""
        if not self.current_period_end:
            return True
        return datetime.utcnow() > self.current_period_end
    
    @property
    def days_remaining(self) -> int:
        """Days until subscription expires"""
        if not self.current_period_end:
            return 0
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)
    
    def can_access_sport(self, sport: str) -> bool:
        """
        Check if user can access a specific sport.
        
        Args:
            sport: "NFL", "NBA", or "NHL"
            
        Returns:
            True if user has access
        """
        if not self.is_active or self.is_expired:
            return False
        
        if self.tier == SubscriptionTier.FREE:
            return False
        elif self.tier == SubscriptionTier.SINGLE_SPORT:
            return self.subscribed_sport == sport
        elif self.tier in [SubscriptionTier.ALL_SPORTS, SubscriptionTier.ELITE]:
            return True
        
        return False
    
    def to_dict(self) -> dict:
        return {
            'tier': self.tier,
            'billing_interval': self.billing_interval,
            'subscribed_sport': self.subscribed_sport,
            'is_active': self.is_active,
            'is_trial': self.is_trial,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'days_remaining': self.days_remaining,
            'cancel_at_period_end': self.cancel_at_period_end,
        }

class UsageTracking(Base):
    """
    Track usage for free tier limits.
    
    Free tier limits:
    - 3 patterns per week
    """
    __tablename__ = 'usage_tracking'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Usage counters (reset weekly for free users)
    patterns_viewed_this_week = Column(Integer, default=0)
    week_start_date = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    last_reset = Column(DateTime, default=datetime.utcnow)
    
    def should_reset(self) -> bool:
        """Check if week has passed (reset counter)"""
        days_since_reset = (datetime.utcnow() - self.last_reset).days
        return days_since_reset >= 7
    
    def reset_weekly_counters(self):
        """Reset weekly usage counters"""
        self.patterns_viewed_this_week = 0
        self.week_start_date = datetime.utcnow()
        self.last_reset = datetime.utcnow()
    
    def can_view_pattern(self, user_tier: str) -> bool:
        """Check if user can view another pattern"""
        # Paid users: unlimited
        if user_tier != SubscriptionTier.FREE:
            return True
        
        # Free users: check limit
        if self.should_reset():
            self.reset_weekly_counters()
        
        return self.patterns_viewed_this_week < 3
    
    def increment_pattern_view(self):
        """Record a pattern view"""
        self.patterns_viewed_this_week += 1
```

**Tests Required:**
- Test subscription tier access logic
- Test sport access permissions
- Test expiration detection
- Test usage tracking limits
- Test weekly reset logic

**Acceptance Criteria:**
- [ ] Subscription model tracks all tiers
- [ ] Sport access control works
- [ ] Usage limits enforce correctly
- [ ] Stripe IDs stored properly

---

#### 12.2 `backend/app/services/stripe_service.py`

**Purpose:** Stripe payment integration.

**Implementation Requirements:**
```python
import stripe
from typing import Dict, Optional
from datetime import datetime

from app.config import settings
from app.models.subscription import Subscription, SubscriptionTier, BillingInterval
from app.database import get_db_session

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    """
    Stripe payment integration.
    
    Why Stripe:
    - Industry standard
    - Simple integration
    - Handles PCI compliance
    - Built-in billing portal
    """
    
    # Stripe Price IDs (create these in Stripe Dashboard)
    PRICE_IDS = {
        SubscriptionTier.SINGLE_SPORT: {
            BillingInterval.MONTHLY: 'price_single_monthly',  # $14.99/month
            BillingInterval.YEARLY: 'price_single_yearly',    # $119/year
        },
        SubscriptionTier.ALL_SPORTS: {
            BillingInterval.MONTHLY: 'price_all_monthly',     # $29.99/month
            BillingInterval.YEARLY: 'price_all_yearly',       # $249/year
        },
        SubscriptionTier.ELITE: {
            BillingInterval.MONTHLY: 'price_elite_monthly',   # $49.99/month
            BillingInterval.YEARLY: 'price_elite_yearly',     # $399/year
        },
    }
    
    def create_customer(self, user_id: str, email: str) -> str:
        """
        Create Stripe customer.
        
        Returns:
            Stripe customer ID
        """
        customer = stripe.Customer.create(
            email=email,
            metadata={'user_id': str(user_id)}
        )
        
        return customer.id
    
    def create_checkout_session(
        self,
        user_id: str,
        tier: SubscriptionTier,
        billing_interval: BillingInterval,
        sport: Optional[str] = None,
        success_url: str = None,
        cancel_url: str = None,
    ) -> Dict:
        """
        Create Stripe Checkout session for subscription.
        
        Args:
            user_id: User ID
            tier: Subscription tier
            billing_interval: Monthly or yearly
            sport: Sport choice (required for SINGLE_SPORT)
            success_url: Redirect URL after success
            cancel_url: Redirect URL after cancel
            
        Returns:
            Checkout session with URL
        """
        # Get or create Stripe customer
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            
            if subscription and subscription.stripe_customer_id:
                customer_id = subscription.stripe_customer_id
            else:
                # Need to get email from user
                from app.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                customer_id = self.create_customer(user_id, user.email)
                
                # Save customer ID
                if not subscription:
                    subscription = Subscription(user_id=user_id)
                    db.add(subscription)
                subscription.stripe_customer_id = customer_id
                db.commit()
        
        # Get price ID
        price_id = self.PRICE_IDS[tier][billing_interval]
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url or f"{settings.FRONTEND_URL}/subscribe/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url or f"{settings.FRONTEND_URL}/subscribe/cancel",
            metadata={
                'user_id': str(user_id),
                'tier': tier,
                'sport': sport or '',
            },
            subscription_data={
                'metadata': {
                    'user_id': str(user_id),
                    'tier': tier,
                    'sport': sport or '',
                }
            },
        )
        
        return {
            'session_id': session.id,
            'url': session.url,
        }
    
    def create_billing_portal_session(self, customer_id: str) -> str:
        """
        Create Stripe billing portal session.
        
        User can manage subscription, update payment, view invoices.
        
        Returns:
            Billing portal URL
        """
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.FRONTEND_URL}/account",
        )
        
        return session.url
    
    def cancel_subscription(self, subscription_id: str, immediate: bool = False):
        """
        Cancel subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            immediate: If True, cancel immediately. If False, cancel at period end.
        """
        if immediate:
            stripe.Subscription.delete(subscription_id)
        else:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
    
    def handle_webhook_event(self, event: Dict):
        """
        Handle Stripe webhook events.
        
        Events to handle:
        - checkout.session.completed (new subscription)
        - customer.subscription.updated (renewal, upgrade, downgrade)
        - customer.subscription.deleted (cancellation)
        - invoice.payment_succeeded (successful payment)
        - invoice.payment_failed (failed payment)
        """
        event_type = event['type']
        
        if event_type == 'checkout.session.completed':
            self._handle_checkout_completed(event['data']['object'])
        
        elif event_type == 'customer.subscription.updated':
            self._handle_subscription_updated(event['data']['object'])
        
        elif event_type == 'customer.subscription.deleted':
            self._handle_subscription_deleted(event['data']['object'])
        
        elif event_type == 'invoice.payment_succeeded':
            self._handle_payment_succeeded(event['data']['object'])
        
        elif event_type == 'invoice.payment_failed':
            self._handle_payment_failed(event['data']['object'])
    
    def _handle_checkout_completed(self, session: Dict):
        """Handle successful checkout"""
        user_id = session['metadata']['user_id']
        tier = session['metadata']['tier']
        sport = session['metadata'].get('sport')
        
        # Get Stripe subscription
        stripe_subscription = stripe.Subscription.retrieve(session['subscription'])
        
        # Update database
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            
            subscription.tier = tier
            subscription.subscribed_sport = sport if sport else None
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.stripe_price_id = stripe_subscription['items']['data'][0]['price']['id']
            subscription.is_active = True
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription['current_period_start'])
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription['current_period_end'])
            
            db.commit()
    
    def _handle_subscription_updated(self, stripe_subscription: Dict):
        """Handle subscription update (renewal, upgrade, etc)"""
        customer_id = stripe_subscription['customer']
        
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                Subscription.stripe_customer_id == customer_id
            ).first()
            
            if subscription:
                subscription.is_active = stripe_subscription['status'] == 'active'
                subscription.current_period_start = datetime.fromtimestamp(stripe_subscription['current_period_start'])
                subscription.current_period_end = datetime.fromtimestamp(stripe_subscription['current_period_end'])
                subscription.cancel_at_period_end = stripe_subscription['cancel_at_period_end']
                
                db.commit()
    
    def _handle_subscription_deleted(self, stripe_subscription: Dict):
        """Handle subscription cancellation"""
        customer_id = stripe_subscription['customer']
        
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                Subscription.stripe_customer_id == customer_id
            ).first()
            
            if subscription:
                subscription.tier = SubscriptionTier.FREE
                subscription.is_active = False
                subscription.canceled_at = datetime.utcnow()
                subscription.subscribed_sport = None
                
                db.commit()
    
    def _handle_payment_succeeded(self, invoice: Dict):
        """Handle successful payment"""
        # Payment went through - subscription already updated by subscription.updated event
        pass
    
    def _handle_payment_failed(self, invoice: Dict):
        """Handle failed payment"""
        # Could send email notification to user
        # Stripe handles retry logic automatically
        pass
```

**Tests Required:**
- Test customer creation
- Test checkout session creation
- Test webhook handling (mock Stripe events)
- Test cancellation flows
- Test billing portal creation

**Acceptance Criteria:**
- [ ] Checkout sessions create correctly
- [ ] Webhooks update subscriptions
- [ ] Cancellations work (immediate and at period end)
- [ ] Billing portal accessible

---

#### 12.3 `backend/app/api/subscriptions.py`

**Purpose:** Subscription management endpoints.

**Implementation Requirements:**
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.subscription import Subscription, SubscriptionTier, BillingInterval
from app.services.stripe_service import StripeService
from app.api.dependencies import get_current_user
from app.models.user import User
from app.config import settings
import stripe

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

@router.get("/current")
def get_current_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's current subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id
    ).first()
    
    if not subscription:
        # Create free tier subscription
        subscription = Subscription(
            user_id=user.id,
            tier=SubscriptionTier.FREE,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return subscription.to_dict()

@router.post("/checkout")
def create_checkout_session(
    checkout_data: dict,
    user: User = Depends(get_current_user),
):
    """
    Create Stripe checkout session.
    
    Body:
        {
            'tier': 'single_sport' | 'all_sports' | 'elite',
            'billing_interval': 'monthly' | 'yearly',
            'sport': 'NFL' (required for single_sport)
        }
    """
    stripe_service = StripeService()
    
    session = stripe_service.create_checkout_session(
        user_id=user.id,
        tier=checkout_data['tier'],
        billing_interval=checkout_data['billing_interval'],
        sport=checkout_data.get('sport'),
    )
    
    return session

@router.get("/billing-portal")
def get_billing_portal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Stripe billing portal URL"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id
    ).first()
    
    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    
    stripe_service = StripeService()
    url = stripe_service.create_billing_portal_session(subscription.stripe_customer_id)
    
    return {'url': url}

@router.post("/cancel")
def cancel_subscription(
    cancel_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel subscription.
    
    Body:
        {
            'immediate': false  // If true, cancel now. If false, at period end.
        }
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id
    ).first()
    
    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    
    stripe_service = StripeService()
    stripe_service.cancel_subscription(
        subscription.stripe_subscription_id,
        immediate=cancel_data.get('immediate', False)
    )
    
    return {'status': 'cancelled'}

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint.
    
    Verifies webhook signature and processes events.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle event
    stripe_service = StripeService()
    stripe_service.handle_webhook_event(event)
    
    return {'status': 'received'}

@router.get("/pricing")
def get_pricing():
    """
    Get pricing information.
    
    Public endpoint - no auth required.
    """
    return {
        'tiers': [
            {
                'id': 'free',
                'name': 'Free',
                'price_monthly': 0,
                'features': [
                    'Persona profile from CSV',
                    '3 patterns per week',
                    'Basic game info',
                ],
            },
            {
                'id': 'single_sport',
                'name': 'Single Sport',
                'price_monthly': 14.99,
                'price_yearly': 119,
                'features': [
                    'Choose NFL, NBA, or NHL',
                    'Unlimited patterns',
                    'Real-time updates',
                    'Watchlist + bet tracking',
                    'Social proof',
                    'Correlation engine',
                ],
            },
            {
                'id': 'all_sports',
                'name': 'All Sports',
                'price_monthly': 29.99,
                'price_yearly': 249,
                'features': [
                    'Access all three sports',
                    'Everything in Single Sport',
                    'Cross-sport insights',
                    'Switch sports anytime',
                ],
            },
            {
                'id': 'elite',
                'name': 'Elite',
                'price_monthly': 49.99,
                'price_yearly': 399,
                'features': [
                    'Everything in All Sports',
                    'Historical backtesting',
                    'API access',
                    'Advanced analytics',
                    'Priority support',
                ],
            },
        ]
    }
```

**Tests Required:**
- Test get current subscription
- Test checkout session creation
- Test billing portal access
- Test cancellation
- Test webhook verification
- Test pricing endpoint

**Acceptance Criteria:**
- [ ] Subscription CRUD works
- [ ] Checkout creates valid sessions
- [ ] Webhooks verify signatures
- [ ] Cancellation flows work
- [ ] Public pricing endpoint accessible

---

#### 12.4 `backend/app/middleware/access_control.py`

**Purpose:** Enforce subscription access control.

**Implementation Requirements:**
```python
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.subscription import Subscription, SubscriptionTier, UsageTracking
from app.api.dependencies import get_current_user
from app.models.user import User

class AccessControl:
    """
    Middleware for enforcing subscription access.
    
    Why middleware:
    - Centralized access logic
    - Consistent across all endpoints
    - Easy to update rules
    """
    
    @staticmethod
    def require_sport_access(sport: str):
        """
        Dependency for endpoints requiring sport access.
        
        Usage:
            @router.get("/nfl/patterns", dependencies=[Depends(AccessControl.require_sport_access("NFL"))])
        """
        def check_access(
            user: User = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user.id
            ).first()
            
            if not subscription:
                raise HTTPException(
                    status_code=402,
                    detail=f"Subscription required to access {sport}"
                )
            
            if not subscription.can_access_sport(sport):
                raise HTTPException(
                    status_code=402,
                    detail={
                        'message': f"Upgrade required to access {sport}",
                        'current_tier': subscription.tier,
                        'required_tier': 'single_sport or higher',
                    }
                )
            
            return True
        
        return check_access
    
    @staticmethod
    def check_pattern_limit(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """
        Check if user can view patterns (free tier limit).
        
        Returns:
            True if allowed, raises HTTPException if not
        """
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        # Paid users: unlimited
        if subscription and subscription.tier != SubscriptionTier.FREE:
            return True
        
        # Free users: check usage
        usage = db.query(UsageTracking).filter(
            UsageTracking.user_id == user.id
        ).first()
        
        if not usage:
            usage = UsageTracking(user_id=user.id)
            db.add(usage)
            db.commit()
        
        if not usage.can_view_pattern(subscription.tier if subscription else SubscriptionTier.FREE):
            raise HTTPException(
                status_code=402,
                detail={
                    'message': 'Pattern limit reached for free tier',
                    'limit': 3,
                    'used': usage.patterns_viewed_this_week,
                    'resets_in_days': 7 - (datetime.utcnow() - usage.week_start_date).days,
                }
            )
        
        # Increment counter
        usage.increment_pattern_view()
        db.commit()
        
        return True
    
    @staticmethod
    def require_elite(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Require Elite tier subscription"""
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        if not subscription or subscription.tier != SubscriptionTier.ELITE:
            raise HTTPException(
                status_code=402,
                detail="Elite subscription required for this feature"
            )
        
        return True
```

**Tests Required:**
- Test sport access enforcement
- Test pattern limit enforcement
- Test elite tier requirement
- Test error responses

**Acceptance Criteria:**
- [ ] Access control enforced correctly
- [ ] Free tier limits work
- [ ] Clear error messages
- [ ] Upgrade prompts included

---

#### 12.5 `frontend/src/pages/Pricing.tsx`

**Purpose:** Pricing page with Stripe checkout integration.

**Implementation Requirements:**
```typescript
import React, { useState } from 'react';
import api from '../services/api';

const Pricing: React.FC = () => {
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'yearly'>('monthly');
  const [loading, setLoading] = useState(false);
  
  const plans = [
    {
      id: 'free',
      name: 'Free',
      monthly: 0,
      yearly: 0,
      features: [
        'Persona profile from CSV',
        '3 patterns per week',
        'Basic game info',
      ],
    },
    {
      id: 'single_sport',
      name: 'Single Sport',
      monthly: 14.99,
      yearly: 119,
      popular: true,
      features: [
        'Choose NFL, NBA, or NHL',
        'Unlimited patterns',
        'Real-time updates',
        'Watchlist + bet tracking',
        'Social proof',
        'Correlation engine',
      ],
    },
    {
      id: 'all_sports',
      name: 'All Sports',
      monthly: 29.99,
      yearly: 249,
      features: [
        'Access all three sports',
        'Everything in Single Sport',
        'Cross-sport insights',
        'Switch sports anytime',
      ],
    },
    {
      id: 'elite',
      name: 'Elite',
      monthly: 49.99,
      yearly: 399,
      features: [
        'Everything in All Sports',
        'Historical backtesting',
        'API access',
        'Advanced analytics',
        'Priority support',
      ],
    },
  ];
  
  const handleSubscribe = async (planId: string) => {
    if (planId === 'free') return;
    
    setLoading(true);
    try {
      let sport = null;
      
      // If single sport, ask which sport
      if (planId === 'single_sport') {
        sport = prompt('Choose your sport (NFL, NBA, or NHL):');
        if (!sport || !['NFL', 'NBA', 'NHL'].includes(sport.toUpperCase())) {
          alert('Invalid sport selection');
          setLoading(false);
          return;
        }
        sport = sport.toUpperCase();
      }
      
      const response = await api.post('/subscriptions/checkout', {
        tier: planId,
        billing_interval: billingInterval,
        sport: sport,
      });
      
      // Redirect to Stripe Checkout
      window.location.href = response.data.url;
    } catch (error) {
      console.error('Error creating checkout:', error);
      alert('Failed to start checkout');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="container mx-auto p-8">
      <h1 className="text-4xl font-bold text-center mb-4">Choose Your Plan</h1>
      <p className="text-center text-gray-600 mb-8">
        Upload your DFS history once, get personalized insights across all your sports.
      </p>
      
      {/* Billing toggle */}
      <div className="flex justify-center mb-8">
        <div className="bg-gray-200 rounded-lg p-1 inline-flex">
          <button
            className={`px-6 py-2 rounded ${billingInterval === 'monthly' ? 'bg-white shadow' : ''}`}
            onClick={() => setBillingInterval('monthly')}
          >
            Monthly
          </button>
          <button
            className={`px-6 py-2 rounded ${billingInterval === 'yearly' ? 'bg-white shadow' : ''}`}
            onClick={() => setBillingInterval('yearly')}
          >
            Yearly
            <span className="ml-2 text-green-600 font-semibold text-sm">Save 33%</span>
          </button>
        </div>
      </div>
      
      {/* Plans */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {plans.map(plan => {
          const price = billingInterval === 'monthly' ? plan.monthly : plan.yearly;
          const priceLabel = billingInterval === 'monthly' ? '/month' : '/year';
          
          return (
            <div 
              key={plan.id}
              className={`border-2 rounded-lg p-6 ${plan.popular ? 'border-blue-500 shadow-lg' : 'border-gray-300'}`}
            >
              {plan.popular && (
                <div className="bg-blue-500 text-white text-xs font-semibold px-3 py-1 rounded-full inline-block mb-4">
                  MOST POPULAR
                </div>
              )}
              
              <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
              <div className="mb-4">
                <span className="text-4xl font-bold">${price}</span>
                <span className="text-gray-600">{priceLabel}</span>
              </div>
              
              <ul className="mb-6 space-y-2">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="text-green-500 mr-2">✓</span>
                    <span className="text-sm">{feature}</span>
                  </li>
                ))}
              </ul>
              
              <button
                onClick={() => handleSubscribe(plan.id)}
                disabled={loading || plan.id === 'free'}
                className={`w-full py-3 rounded font-semibold ${
                  plan.id === 'free'
                    ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                    : plan.popular
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-800 text-white hover:bg-gray-900'
                }`}
              >
                {plan.id === 'free' ? 'Current Plan' : 'Subscribe'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Pricing;
```

**Tests Required:**
- Test plan display
- Test billing toggle
- Test checkout flow
- Test sport selection for single sport tier

**Acceptance Criteria:**
- [ ] All plans display correctly
- [ ] Billing toggle works
- [ ] Checkout redirects to Stripe
- [ ] Sport selection for single sport works

---

### Phase 12 Checkpoint

**Before launch:**
- [ ] Stripe integration complete
- [ ] Subscription tiers working
- [ ] Access control enforced
- [ ] Webhooks handling events
- [ ] Billing portal accessible
- [ ] Pricing page functional
- [ ] Free tier limits enforced
- [ ] Upgrade/downgrade flows tested

---

## Final Integration Checklist

**Complete Magic Layer + Subscriptions:**
- [ ] Social proof tracking active
- [ ] Watchlist system functional
- [ ] Bet tracking working
- [ ] Correlation engine detecting
- [ ] Advanced patterns running
- [ ] Subscription tiers enforced
- [ ] Stripe payments processing
- [ ] All frontend components integrated

**Performance:**
- [ ] Social proof aggregation < 100ms
- [ ] Correlation calculation < 200ms
- [ ] Pattern detection < 2s
- [ ] WebSocket updates < 500ms
- [ ] Stripe checkout < 1s

**User Experience:**
- [ ] Onboarding flow smooth
- [ ] Persona insights clear
- [ ] Watchlist intuitive
- [ ] Correlation warnings helpful
- [ ] Pricing page clear
- [ ] Upgrade prompts non-intrusive

**Business Operations:**
- [ ] Stripe webhook monitoring
- [ ] Failed payment handling
- [ ] Refund process documented
- [ ] Customer support flow
- [ ] Churn tracking

---

## Deployment Strategy

**Week 1: Foundation (Core Specs)**
- DFS Parser
- ThirdDownIQ Core

**Week 2: Magic Layer (Phases 7-11)**
- Social proof
- Watchlist/bets
- Correlations
- Advanced patterns

**Week 3: Monetization (Phase 12) + Launch**
- Stripe integration
- Subscription system
- Access control
- Pricing page
- Bug fixes
- Performance tuning
- Marketing site
- **GO LIVE**

---

**This completes the full system - from free CSV upload to paid Elite subscriptions. Ready to build and ship.**
