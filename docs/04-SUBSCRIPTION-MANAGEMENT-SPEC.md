# Subscription Management - Stripe Integration Spec

## Overview
**Purpose:** Implement tiered subscription system with Stripe for FantasyIQ platform.

**Tiers:**
- Free: Persona + 3 patterns/week
- Single Sport ($14.99/month or $119/year): One sport, full features
- All Sports ($29.99/month or $249/year): Three sports, full features  
- Elite ($49.99/month or $399/year): Everything + API access, exports

**Architecture:** Shared subscription service used by all sport apps (NFL/NBA/NHL)

---

## Phase 1: Stripe Setup & Models

### 1.1 Subscription Tier Model
**File:** `src/models/subscription_tier.py`

```python
from enum import Enum
from decimal import Decimal

class SubscriptionTier(str, Enum):
    """Subscription tier levels"""
    FREE = "free"
    SINGLE_SPORT = "single_sport"
    ALL_SPORTS = "all_sports"
    ELITE = "elite"

class TierConfig:
    """Configuration for each tier"""
    
    TIERS = {
        SubscriptionTier.FREE: {
            "name": "Free",
            "price_monthly": Decimal("0"),
            "price_yearly": Decimal("0"),
            "sports_allowed": 0,  # Can view but not access full features
            "patterns_per_week": 3,
            "features": ["persona_profile", "basic_patterns"],
            "stripe_price_id_monthly": None,
            "stripe_price_id_yearly": None
        },
        SubscriptionTier.SINGLE_SPORT: {
            "name": "Single Sport",
            "price_monthly": Decimal("14.99"),
            "price_yearly": Decimal("119"),  # ~$10/month
            "sports_allowed": 1,
            "patterns_per_week": None,  # Unlimited
            "features": [
                "unlimited_patterns",
                "real_time_updates",
                "watchlist",
                "bet_tracking",
                "social_proof",
                "correlations"
            ],
            "stripe_price_id_monthly": "price_single_sport_monthly",
            "stripe_price_id_yearly": "price_single_sport_yearly"
        },
        SubscriptionTier.ALL_SPORTS: {
            "name": "All Sports",
            "price_monthly": Decimal("29.99"),
            "price_yearly": Decimal("249"),  # ~$21/month
            "sports_allowed": 3,  # NFL, NBA, NHL
            "patterns_per_week": None,
            "features": [
                "unlimited_patterns",
                "real_time_updates",
                "watchlist",
                "bet_tracking",
                "social_proof",
                "correlations",
                "cross_sport_insights"
            ],
            "stripe_price_id_monthly": "price_all_sports_monthly",
            "stripe_price_id_yearly": "price_all_sports_yearly"
        },
        SubscriptionTier.ELITE: {
            "name": "Elite",
            "price_monthly": Decimal("49.99"),
            "price_yearly": Decimal("399"),  # ~$33/month
            "sports_allowed": 3,
            "patterns_per_week": None,
            "features": [
                "unlimited_patterns",
                "real_time_updates",
                "watchlist",
                "bet_tracking",
                "social_proof",
                "correlations",
                "cross_sport_insights",
                "historical_backtesting",
                "api_access",
                "data_exports",
                "priority_support"
            ],
            "stripe_price_id_monthly": "price_elite_monthly",
            "stripe_price_id_yearly": "price_elite_yearly"
        }
    }
```

### 1.2 User Subscription Model
**File:** `src/models/user_subscription.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .subscription_tier import SubscriptionTier

class UserSubscription(BaseModel):
    """
    User's current subscription state.
    Why: Track what features user has access to.
    """
    user_id: str
    tier: SubscriptionTier = SubscriptionTier.FREE
    
    # Billing
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_interval: Optional[str] = None  # "month" or "year"
    
    # Access
    subscribed_sport: Optional[str] = None  # For SINGLE_SPORT tier
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    
    # Status
    status: str = "active"  # "active", "canceled", "past_due", "expired"
    cancel_at_period_end: bool = False
    
    # Metadata
    created_at: datetime
    updated_at: datetime
```

---

## Phase 2: Stripe Client

### 2.1 Stripe Service
**File:** `src/services/stripe_client.py`

```python
import stripe
import os
from typing import Optional
from ..models.subscription_tier import SubscriptionTier, TierConfig

class StripeClient:
    """
    Wrapper for Stripe API operations.
    Why: Centralize Stripe logic, handle errors consistently.
    """
    
    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    def create_customer(self, user_id: str, email: str) -> str:
        """
        Create Stripe customer for user.
        Returns: Stripe customer ID
        """
        customer = stripe.Customer.create(
            email=email,
            metadata={"user_id": user_id}
        )
        return customer.id
    
    def create_subscription(
        self, 
        customer_id: str,
        tier: SubscriptionTier,
        interval: str = "month",
        sport: Optional[str] = None
    ) -> dict:
        """
        Create new subscription for customer.
        Returns: Stripe subscription object
        """
        config = TierConfig.TIERS[tier]
        
        # Get correct price ID based on interval
        if interval == "year":
            price_id = config["stripe_price_id_yearly"]
        else:
            price_id = config["stripe_price_id_monthly"]
        
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            metadata={
                "tier": tier.value,
                "sport": sport  # For single sport tier
            }
        )
        
        return subscription
    
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True):
        """
        Cancel subscription.
        If at_period_end=True, cancel at end of billing period.
        If False, cancel immediately.
        """
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=at_period_end
        )
    
    def update_subscription(
        self,
        subscription_id: str,
        new_tier: SubscriptionTier,
        interval: str = "month"
    ):
        """
        Upgrade/downgrade subscription to new tier.
        Prorates automatically.
        """
        config = TierConfig.TIERS[new_tier]
        
        if interval == "year":
            new_price_id = config["stripe_price_id_yearly"]
        else:
            new_price_id = config["stripe_price_id_monthly"]
        
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": subscription["items"]["data"][0]["id"],
                "price": new_price_id
            }],
            proration_behavior="always_invoice"
        )
    
    def create_checkout_session(
        self,
        customer_id: str,
        tier: SubscriptionTier,
        interval: str,
        success_url: str,
        cancel_url: str
    ) -> str:
        """
        Create Stripe Checkout session for subscription.
        Returns: Checkout session URL
        """
        config = TierConfig.TIERS[tier]
        
        if interval == "year":
            price_id = config["stripe_price_id_yearly"]
        else:
            price_id = config["stripe_price_id_monthly"]
        
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tier": tier.value
            }
        )
        
        return session.url
    
    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> dict:
        """
        Verify webhook came from Stripe.
        Returns: Webhook event object
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise Exception("Invalid signature")
```

---

## Phase 3: Subscription Manager

### 3.1 Subscription Service
**File:** `src/services/subscription_manager.py`

```python
from typing import Optional
from datetime import datetime
from ..models.user_subscription import UserSubscription
from ..models.subscription_tier import SubscriptionTier
from .stripe_client import StripeClient

class SubscriptionManager:
    """
    Manage user subscriptions and access control.
    Why: Business logic layer between Stripe and app.
    """
    
    def __init__(self, db, stripe_client: StripeClient):
        self.db = db
        self.stripe = stripe_client
    
    async def get_user_subscription(self, user_id: str) -> UserSubscription:
        """Get user's current subscription"""
        sub = await self.db.get_subscription(user_id)
        
        if not sub:
            # Create default free subscription
            sub = UserSubscription(
                user_id=user_id,
                tier=SubscriptionTier.FREE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await self.db.create_subscription(sub)
        
        return sub
    
    async def create_subscription(
        self,
        user_id: str,
        email: str,
        tier: SubscriptionTier,
        interval: str = "month",
        sport: Optional[str] = None
    ) -> str:
        """
        Start new subscription for user.
        Returns: Checkout URL
        """
        # Get or create Stripe customer
        sub = await self.get_user_subscription(user_id)
        
        if not sub.stripe_customer_id:
            customer_id = self.stripe.create_customer(user_id, email)
            sub.stripe_customer_id = customer_id
            await self.db.update_subscription(sub)
        
        # Create checkout session
        checkout_url = self.stripe.create_checkout_session(
            customer_id=sub.stripe_customer_id,
            tier=tier,
            interval=interval,
            success_url=f"https://fantasyiq.io/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://fantasyiq.io/pricing"
        )
        
        return checkout_url
    
    async def activate_subscription(
        self,
        user_id: str,
        stripe_subscription_id: str,
        tier: SubscriptionTier,
        interval: str,
        sport: Optional[str] = None
    ):
        """
        Activate subscription after successful payment.
        Called by webhook handler.
        """
        sub = await self.get_user_subscription(user_id)
        
        sub.tier = tier
        sub.stripe_subscription_id = stripe_subscription_id
        sub.billing_interval = interval
        sub.subscribed_sport = sport
        sub.subscription_start = datetime.utcnow()
        sub.status = "active"
        sub.updated_at = datetime.utcnow()
        
        await self.db.update_subscription(sub)
    
    async def cancel_subscription(self, user_id: str, immediate: bool = False):
        """Cancel user's subscription"""
        sub = await self.get_user_subscription(user_id)
        
        if not sub.stripe_subscription_id:
            raise Exception("No active subscription")
        
        # Cancel in Stripe
        self.stripe.cancel_subscription(
            sub.stripe_subscription_id,
            at_period_end=not immediate
        )
        
        if immediate:
            sub.tier = SubscriptionTier.FREE
            sub.status = "canceled"
            sub.subscription_end = datetime.utcnow()
        else:
            sub.cancel_at_period_end = True
        
        sub.updated_at = datetime.utcnow()
        await self.db.update_subscription(sub)
    
    async def upgrade_subscription(
        self,
        user_id: str,
        new_tier: SubscriptionTier,
        new_sport: Optional[str] = None
    ):
        """Upgrade/downgrade subscription"""
        sub = await self.get_user_subscription(user_id)
        
        if not sub.stripe_subscription_id:
            raise Exception("No active subscription to upgrade")
        
        # Update in Stripe (prorate automatically)
        self.stripe.update_subscription(
            sub.stripe_subscription_id,
            new_tier,
            sub.billing_interval
        )
        
        # Update locally
        sub.tier = new_tier
        if new_tier == SubscriptionTier.SINGLE_SPORT:
            sub.subscribed_sport = new_sport
        sub.updated_at = datetime.utcnow()
        
        await self.db.update_subscription(sub)
    
    def user_can_access_sport(self, sub: UserSubscription, sport: str) -> bool:
        """Check if user can access specific sport"""
        if sub.tier == SubscriptionTier.FREE:
            return False
        
        if sub.tier == SubscriptionTier.SINGLE_SPORT:
            return sub.subscribed_sport == sport
        
        if sub.tier in [SubscriptionTier.ALL_SPORTS, SubscriptionTier.ELITE]:
            return True
        
        return False
    
    def user_can_access_feature(self, sub: UserSubscription, feature: str) -> bool:
        """Check if user's tier includes feature"""
        config = TierConfig.TIERS[sub.tier]
        return feature in config["features"]
```

---

## Phase 4: Webhook Handler

### 4.1 Stripe Webhooks
**File:** `src/services/webhook_handler.py`

```python
from .stripe_client import StripeClient
from .subscription_manager import SubscriptionManager
from ..models.subscription_tier import SubscriptionTier

class WebhookHandler:
    """
    Handle Stripe webhook events.
    Why: Keep subscription status in sync with Stripe.
    """
    
    def __init__(self, subscription_manager: SubscriptionManager):
        self.subscription_manager = subscription_manager
    
    async def handle_event(self, event: dict):
        """
        Route webhook event to appropriate handler.
        Returns: Success/failure status
        """
        event_type = event["type"]
        
        handlers = {
            "checkout.session.completed": self.handle_checkout_completed,
            "customer.subscription.updated": self.handle_subscription_updated,
            "customer.subscription.deleted": self.handle_subscription_deleted,
            "invoice.payment_failed": self.handle_payment_failed,
            "invoice.payment_succeeded": self.handle_payment_succeeded
        }
        
        handler = handlers.get(event_type)
        
        if handler:
            await handler(event["data"]["object"])
            return {"status": "handled"}
        else:
            print(f"Unhandled event type: {event_type}")
            return {"status": "ignored"}
    
    async def handle_checkout_completed(self, session: dict):
        """
        User completed checkout - activate subscription.
        """
        customer_id = session["customer"]
        subscription_id = session["subscription"]
        
        # Get user_id from customer metadata
        import stripe
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.metadata["user_id"]
        
        # Get subscription details
        subscription = stripe.Subscription.retrieve(subscription_id)
        tier = SubscriptionTier(subscription.metadata["tier"])
        interval = subscription.items.data[0].plan.interval
        sport = subscription.metadata.get("sport")
        
        # Activate in our system
        await self.subscription_manager.activate_subscription(
            user_id=user_id,
            stripe_subscription_id=subscription_id,
            tier=tier,
            interval=interval,
            sport=sport
        )
    
    async def handle_subscription_updated(self, subscription: dict):
        """
        Subscription changed (upgraded, downgraded, etc).
        """
        customer_id = subscription["customer"]
        
        # Get user_id
        import stripe
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.metadata["user_id"]
        
        # Check if canceled
        if subscription.get("cancel_at_period_end"):
            await self.subscription_manager.cancel_subscription(
                user_id,
                immediate=False
            )
    
    async def handle_subscription_deleted(self, subscription: dict):
        """
        Subscription ended - downgrade to free.
        """
        customer_id = subscription["customer"]
        
        import stripe
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.metadata["user_id"]
        
        # Downgrade to free
        sub = await self.subscription_manager.get_user_subscription(user_id)
        sub.tier = SubscriptionTier.FREE
        sub.status = "canceled"
        sub.subscription_end = datetime.utcnow()
        
        await self.subscription_manager.db.update_subscription(sub)
    
    async def handle_payment_failed(self, invoice: dict):
        """
        Payment failed - mark subscription as past_due.
        """
        customer_id = invoice["customer"]
        
        import stripe
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.metadata["user_id"]
        
        # Mark as past due
        sub = await self.subscription_manager.get_user_subscription(user_id)
        sub.status = "past_due"
        
        await self.subscription_manager.db.update_subscription(sub)
        
        # TODO: Send email to user
    
    async def handle_payment_succeeded(self, invoice: dict):
        """
        Payment succeeded - ensure status is active.
        """
        customer_id = invoice["customer"]
        
        import stripe
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.metadata["user_id"]
        
        # Ensure active status
        sub = await self.subscription_manager.get_user_subscription(user_id)
        if sub.status == "past_due":
            sub.status = "active"
            await self.subscription_manager.db.update_subscription(sub)
```

---

## Phase 5: API Endpoints

### 5.1 Subscription API
**File:** `src/api/subscriptions.py`

```python
from fastapi import APIRouter, Depends, Request
from ..models.subscription_tier import SubscriptionTier
from ..services.subscription_manager import SubscriptionManager
from ..services.webhook_handler import WebhookHandler
from ..services.stripe_client import StripeClient

router = APIRouter()

@router.get("/subscription/{user_id}")
async def get_subscription(
    user_id: str,
    manager: SubscriptionManager = Depends()
):
    """Get user's current subscription"""
    sub = await manager.get_user_subscription(user_id)
    return sub

@router.post("/subscription/checkout")
async def create_checkout(
    user_id: str,
    email: str,
    tier: SubscriptionTier,
    interval: str = "month",
    sport: str = None,
    manager: SubscriptionManager = Depends()
):
    """
    Create Stripe checkout session.
    Returns: Checkout URL to redirect user to
    """
    checkout_url = await manager.create_subscription(
        user_id, email, tier, interval, sport
    )
    return {"checkout_url": checkout_url}

@router.post("/subscription/cancel")
async def cancel_subscription(
    user_id: str,
    immediate: bool = False,
    manager: SubscriptionManager = Depends()
):
    """Cancel subscription"""
    await manager.cancel_subscription(user_id, immediate)
    return {"status": "canceled"}

@router.post("/subscription/upgrade")
async def upgrade_subscription(
    user_id: str,
    new_tier: SubscriptionTier,
    new_sport: str = None,
    manager: SubscriptionManager = Depends()
):
    """Upgrade/downgrade subscription"""
    await manager.upgrade_subscription(user_id, new_tier, new_sport)
    return {"status": "updated"}

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_client: StripeClient = Depends(),
    handler: WebhookHandler = Depends()
):
    """
    Stripe webhook endpoint.
    Receives events when subscription status changes.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe_client.verify_webhook_signature(payload, sig_header)
    except Exception as e:
        return {"error": str(e)}, 400
    
    # Handle event
    result = await handler.handle_event(event)
    
    return result
```

---

## Phase 6: Access Control Middleware

### 6.1 Feature Gate Decorator
**File:** `src/middleware/access_control.py`

```python
from functools import wraps
from fastapi import HTTPException, Depends
from ..services.subscription_manager import SubscriptionManager

def require_feature(feature: str):
    """
    Decorator to require specific feature access.
    Usage: @require_feature("unlimited_patterns")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user_id: str, manager: SubscriptionManager = Depends(), **kwargs):
            sub = await manager.get_user_subscription(user_id)
            
            if not manager.user_can_access_feature(sub, feature):
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature}' requires {sub.tier.value} or higher"
                )
            
            return await func(*args, user_id=user_id, manager=manager, **kwargs)
        
        return wrapper
    return decorator

def require_sport_access(sport: str):
    """
    Decorator to require access to specific sport.
    Usage: @require_sport_access("NFL")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user_id: str, manager: SubscriptionManager = Depends(), **kwargs):
            sub = await manager.get_user_subscription(user_id)
            
            if not manager.user_can_access_sport(sub, sport):
                raise HTTPException(
                    status_code=403,
                    detail=f"Access to {sport} requires subscription"
                )
            
            return await func(*args, user_id=user_id, manager=manager, **kwargs)
        
        return wrapper
    return decorator
```

### 6.2 Usage in Sport Apps
**File:** `thirddowniq/backend/app/api/patterns.py`

```python
from middleware.access_control import require_sport_access, require_feature

@router.get("/patterns/{game_id}")
@require_sport_access("NFL")
@require_feature("unlimited_patterns")
async def get_patterns(
    game_id: str,
    user_id: str,
    manager: SubscriptionManager = Depends()
):
    """Get patterns - requires NFL access + unlimited patterns feature"""
    # ... pattern logic
    pass
```

---

## Phase 7: Database Schema

```sql
CREATE TABLE user_subscriptions (
    user_id VARCHAR PRIMARY KEY,
    tier VARCHAR NOT NULL DEFAULT 'free',
    
    -- Stripe IDs
    stripe_customer_id VARCHAR,
    stripe_subscription_id VARCHAR,
    billing_interval VARCHAR,  -- 'month' or 'year'
    
    -- Access
    subscribed_sport VARCHAR,  -- For single_sport tier
    subscription_start TIMESTAMP,
    subscription_end TIMESTAMP,
    
    -- Status
    status VARCHAR DEFAULT 'active',  -- 'active', 'canceled', 'past_due', 'expired'
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_subscription_status (user_id, status),
    INDEX idx_subscription_stripe (stripe_subscription_id)
);

CREATE TABLE payment_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    stripe_invoice_id VARCHAR NOT NULL,
    amount DECIMAL(8,2) NOT NULL,
    status VARCHAR NOT NULL,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_payment_user (user_id, created_at DESC)
);
```

---

## Phase 8: Frontend Components

### 8.1 Pricing Page
**File:** `frontend/src/pages/Pricing.jsx`

```jsx
function PricingPage() {
  const tiers = [
    {
      name: "Free",
      price: "$0",
      interval: "forever",
      features: [
        "Persona profile from CSV",
        "3 patterns per week",
        "Basic insights"
      ],
      cta: "Get Started",
      tier: "free"
    },
    {
      name: "Single Sport",
      price: "$14.99",
      priceYearly: "$119",
      interval: "/month",
      features: [
        "Full access to ONE sport",
        "Unlimited patterns",
        "Watchlist & bet tracking",
        "Real-time updates",
        "Social proof"
      ],
      cta: "Start Free Trial",
      tier: "single_sport",
      popular: false
    },
    {
      name: "All Sports",
      price: "$29.99",
      priceYearly: "$249",
      interval: "/month",
      features: [
        "NFL + NBA + NHL access",
        "Everything in Single Sport",
        "Cross-sport insights",
        "Priority support"
      ],
      cta: "Start Free Trial",
      tier: "all_sports",
      popular: true
    },
    {
      name: "Elite",
      price: "$49.99",
      priceYearly: "$399",
      interval: "/month",
      features: [
        "Everything in All Sports",
        "Historical backtesting",
        "API access",
        "Data exports",
        "Early access to features"
      ],
      cta: "Start Free Trial",
      tier: "elite",
      popular: false
    }
  ];
  
  const [billingInterval, setBillingInterval] = useState("month");
  
  const handleSubscribe = async (tier, interval) => {
    const response = await fetch('/api/subscription/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: currentUser.id,
        email: currentUser.email,
        tier: tier,
        interval: interval
      })
    });
    
    const { checkout_url } = await response.json();
    window.location.href = checkout_url;
  };
  
  return (
    <div className="pricing-page">
      <h1>Choose Your Plan</h1>
      
      <div className="billing-toggle">
        <button 
          onClick={() => setBillingInterval("month")}
          className={billingInterval === "month" ? "active" : ""}
        >
          Monthly
        </button>
        <button 
          onClick={() => setBillingInterval("year")}
          className={billingInterval === "year" ? "active" : ""}
        >
          Yearly <span className="save">Save 20%</span>
        </button>
      </div>
      
      <div className="tiers">
        {tiers.map(tier => (
          <PricingTier 
            key={tier.tier}
            tier={tier}
            interval={billingInterval}
            onSubscribe={handleSubscribe}
          />
        ))}
      </div>
    </div>
  );
}
```

### 8.2 Subscription Management
**File:** `frontend/src/pages/Subscription.jsx`

```jsx
function SubscriptionManagement() {
  const { data: subscription } = useQuery(
    ['subscription', userId],
    () => fetch(`/api/subscription/${userId}`).then(r => r.json())
  );
  
  const handleCancel = async () => {
    if (confirm("Cancel subscription? You'll lose access at end of billing period.")) {
      await fetch('/api/subscription/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, immediate: false })
      });
      
      refetch();
    }
  };
  
  const handleUpgrade = async (newTier) => {
    await fetch('/api/subscription/upgrade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        new_tier: newTier
      })
    });
    
    refetch();
  };
  
  return (
    <div className="subscription-management">
      <h1>Your Subscription</h1>
      
      <div className="current-plan">
        <h2>{subscription.tier}</h2>
        <p>Billed {subscription.billing_interval}ly</p>
        
        {subscription.cancel_at_period_end && (
          <div className="warning">
            Cancels on {formatDate(subscription.subscription_end)}
          </div>
        )}
      </div>
      
      <div className="actions">
        {subscription.tier !== "elite" && (
          <button onClick={() => handleUpgrade("elite")}>
            Upgrade to Elite
          </button>
        )}
        
        {subscription.tier !== "free" && (
          <button onClick={handleCancel} className="danger">
            Cancel Subscription
          </button>
        )}
      </div>
    </div>
  );
}
```

---

## Phase 9: Testing

### 9.1 Subscription Flow Tests
**File:** `tests/test_subscription_flow.py`

```python
import pytest
from src.services.subscription_manager import SubscriptionManager
from src.models.subscription_tier import SubscriptionTier

@pytest.mark.asyncio
async def test_create_subscription(subscription_manager):
    """User can create new subscription"""
    checkout_url = await subscription_manager.create_subscription(
        user_id="user123",
        email="test@example.com",
        tier=SubscriptionTier.ALL_SPORTS,
        interval="month"
    )
    
    assert "checkout.stripe.com" in checkout_url

@pytest.mark.asyncio
async def test_access_control_single_sport(subscription_manager):
    """Single sport subscription only allows one sport"""
    # Activate subscription
    await subscription_manager.activate_subscription(
        user_id="user123",
        stripe_subscription_id="sub_test",
        tier=SubscriptionTier.SINGLE_SPORT,
        interval="month",
        sport="NFL"
    )
    
    sub = await subscription_manager.get_user_subscription("user123")
    
    # Can access NFL
    assert subscription_manager.user_can_access_sport(sub, "NFL") == True
    
    # Cannot access NBA
    assert subscription_manager.user_can_access_sport(sub, "NBA") == False

@pytest.mark.asyncio
async def test_upgrade_subscription(subscription_manager):
    """User can upgrade from single sport to all sports"""
    # Start with single sport
    await subscription_manager.activate_subscription(
        user_id="user123",
        stripe_subscription_id="sub_test",
        tier=SubscriptionTier.SINGLE_SPORT,
        interval="month",
        sport="NFL"
    )
    
    # Upgrade
    await subscription_manager.upgrade_subscription(
        user_id="user123",
        new_tier=SubscriptionTier.ALL_SPORTS
    )
    
    sub = await subscription_manager.get_user_subscription("user123")
    
    assert sub.tier == SubscriptionTier.ALL_SPORTS
    assert subscription_manager.user_can_access_sport(sub, "NBA") == True
```

---

## Success Criteria

**Stripe Integration:**
- ✅ Create subscriptions via Checkout
- ✅ Webhooks handle all events correctly
- ✅ Subscription status synced with Stripe
- ✅ Upgrades/downgrades prorate automatically

**Access Control:**
- ✅ Free users limited to 3 patterns/week
- ✅ Single sport users can only access chosen sport
- ✅ All sports users can access NFL/NBA/NHL
- ✅ Elite users have API access

**Billing:**
- ✅ Monthly and yearly billing work
- ✅ Payment failures handled gracefully
- ✅ Cancellations work (immediate and at period end)
- ✅ Payment history tracked

**Frontend:**
- ✅ Pricing page displays all tiers
- ✅ Checkout redirects to Stripe
- ✅ Subscription management page works
- ✅ Upgrade/downgrade flows work

---

## Build Order

**Night 1:** Models + Stripe Client (Phases 1-2)
**Night 2:** Subscription Manager (Phase 3)
**Night 3:** Webhook Handler (Phase 4)
**Night 4:** API Endpoints + Access Control (Phases 5-6)
**Night 5:** Frontend Components (Phase 8)
**Night 6:** Testing (Phase 9)

---

**This completes the subscription system. All sport apps share this service for billing.**
