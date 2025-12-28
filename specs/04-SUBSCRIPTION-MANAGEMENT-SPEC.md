# Subscription Management & Payment Integration - Phase 12 Spec

## Overview

**Purpose:** Implement Stripe-based subscription management with tiered access control for FantasyIQ platform.

**Prerequisites:**
- DFS Parser (complete)
- ThirdDownIQ Core (complete)
- Magic Layer (complete)

**This phase adds:**
- Stripe payment integration
- Subscription tier enforcement
- Upgrade/downgrade flows
- Usage limits (free tier)
- Payment webhooks
- Billing portal

---

## Subscription Tiers (Reminder)

```
FREE
├── Persona profile from CSV upload
├── 3 patterns per week
└── No real-time updates

SINGLE SPORT ($14.99/month or $119/year)
├── One sport (NFL, NBA, or NHL)
├── Unlimited patterns
├── Real-time updates
├── Watchlist + bet tracking
├── Social proof
└── Correlation engine

ALL SPORTS ($29.99/month or $249/year)
├── All three sports
├── Everything in Single Sport
├── Cross-sport insights
└── Switch sports anytime

ELITE ($49.99/month or $399/year)
├── Everything in All Sports
├── Historical backtesting
├── API access
├── Advanced analytics
├── Priority support
└── Early access to new features
```

---

## Technology Stack

**Payment Processing:**
- Stripe (payment gateway)
- Stripe Customer Portal (self-service billing)
- Stripe Webhooks (event handling)

**Backend:**
- FastAPI (subscription API)
- PostgreSQL (subscription data)
- Redis (rate limiting)

**Frontend:**
- Stripe.js (checkout)
- Stripe Elements (payment forms)

---

## Project Structure

```
shared/subscription-service/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── subscription.py        # Subscription model
│   │   ├── customer.py            # Stripe customer model
│   │   └── payment_history.py    # Payment records
│   ├── services/
│   │   ├── __init__.py
│   │   ├── stripe_service.py      # Stripe API wrapper
│   │   ├── subscription_manager.py # Subscription logic
│   │   └── usage_tracker.py       # Free tier limits
│   ├── api/
│   │   ├── __init__.py
│   │   ├── checkout.py            # Checkout endpoints
│   │   ├── portal.py              # Customer portal
│   │   ├── webhooks.py            # Stripe webhooks
│   │   └── subscriptions.py      # Subscription mgmt
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── subscription_required.py # Paywall middleware
│   └── utils/
│       ├── __init__.py
│       └── constants.py
└── tests/
    ├── test_stripe_service.py
    ├── test_subscription_manager.py
    └── test_webhooks.py
```

---

## Phase 12.1: Data Models

### Files to Create

#### 12.1.1 `src/models/customer.py`

**Purpose:** Stripe customer representation.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.database import Base

class StripeCustomer(Base):
    """
    Link between User and Stripe Customer.
    
    Why separate:
    - User can exist without Stripe
    - Stripe customer ID needed for all operations
    - Track Stripe-specific metadata
    """
    __tablename__ = 'stripe_customers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    
    # Stripe data
    stripe_customer_id = Column(String, unique=True, nullable=False)
    stripe_email = Column(String)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="customer")
    payment_history = relationship("PaymentHistory", back_populates="customer")
    
    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'stripe_customer_id': self.stripe_customer_id,
            'stripe_email': self.stripe_email,
            'created_at': self.created_at.isoformat(),
        }
```

**Tests Required:**
- Test customer creation
- Test user_id uniqueness
- Test stripe_customer_id uniqueness
- Test to_dict() serialization

**Acceptance Criteria:**
- [ ] Customers created correctly
- [ ] Unique constraints enforced
- [ ] Relationships work

---

#### 12.1.2 `src/models/subscription.py`

**Purpose:** Active subscription tracking.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from src.database import Base

class SubscriptionTier(str, Enum):
    FREE = "free"
    SINGLE_SPORT = "single_sport"
    ALL_SPORTS = "all_sports"
    ELITE = "elite"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"

class Subscription(Base):
    """
    Active subscription details.
    
    Why track:
    - Enforce access control
    - Handle upgrades/downgrades
    - Manage cancellations
    - Track billing cycles
    """
    __tablename__ = 'subscriptions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('stripe_customers.id'), nullable=False)
    
    # Stripe data
    stripe_subscription_id = Column(String, unique=True, nullable=False)
    stripe_price_id = Column(String, nullable=False)  # Stripe Price ID
    
    # Subscription details
    tier = Column(String, nullable=False)  # FREE, SINGLE_SPORT, ALL_SPORTS, ELITE
    status = Column(String, nullable=False)  # ACTIVE, CANCELED, etc.
    sport = Column(String)  # "NFL", "NBA", "NHL" (if SINGLE_SPORT)
    
    # Billing
    amount = Column(DECIMAL(10, 2), nullable=False)  # $14.99, $29.99, etc.
    interval = Column(String, nullable=False)  # 'month' or 'year'
    
    # Dates
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("StripeCustomer", back_populates="subscriptions")
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return (
            self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING] and
            self.current_period_end > datetime.utcnow()
        )
    
    @property
    def days_remaining(self) -> int:
        """Days until next billing or end"""
        if not self.is_active:
            return 0
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)
    
    def can_access_sport(self, sport: str) -> bool:
        """Check if subscription allows access to sport"""
        if self.tier == SubscriptionTier.FREE:
            return False
        elif self.tier == SubscriptionTier.SINGLE_SPORT:
            return self.sport == sport
        elif self.tier in [SubscriptionTier.ALL_SPORTS, SubscriptionTier.ELITE]:
            return True
        return False
    
    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'tier': self.tier,
            'status': self.status,
            'sport': self.sport,
            'amount': str(self.amount),
            'interval': self.interval,
            'current_period_start': self.current_period_start.isoformat(),
            'current_period_end': self.current_period_end.isoformat(),
            'cancel_at_period_end': self.cancel_at_period_end,
            'is_active': self.is_active,
            'days_remaining': self.days_remaining,
        }
```

**Tests Required:**
- Test subscription creation
- Test is_active property
- Test days_remaining calculation
- Test can_access_sport() logic
- Test tier access rules

**Acceptance Criteria:**
- [ ] Subscriptions tracked correctly
- [ ] is_active works properly
- [ ] Sport access control accurate
- [ ] Tier logic correct

---

#### 12.1.3 `src/models/payment_history.py`

**Purpose:** Payment record tracking.

**Implementation Requirements:**
```python
from sqlalchemy import Column, String, Integer, DateTime, DECIMAL, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.database import Base

class PaymentHistory(Base):
    """
    Historical payment records.
    
    Why track:
    - Tax reporting
    - Refund handling
    - Revenue analytics
    - Audit trail
    """
    __tablename__ = 'payment_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('stripe_customers.id'), nullable=False)
    
    # Stripe data
    stripe_payment_intent_id = Column(String, unique=True, nullable=False)
    stripe_charge_id = Column(String)
    
    # Payment details
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String, default='usd')
    status = Column(String, nullable=False)  # 'succeeded', 'failed', 'refunded'
    
    # Metadata
    description = Column(String)  # "Single Sport - NFL (Monthly)"
    receipt_url = Column(String)  # Stripe receipt URL
    
    # Dates
    paid_at = Column(DateTime)
    refunded_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("StripeCustomer", back_populates="payment_history")
    
    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'amount': str(self.amount),
            'currency': self.currency,
            'status': self.status,
            'description': self.description,
            'receipt_url': self.receipt_url,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'created_at': self.created_at.isoformat(),
        }
```

**Tests Required:**
- Test payment record creation
- Test status transitions
- Test to_dict() serialization

**Acceptance Criteria:**
- [ ] Payments tracked correctly
- [ ] Refunds tracked
- [ ] Serialization works

---

## Phase 12.2: Stripe Service Integration

### Files to Create

#### 12.2.1 `src/services/stripe_service.py`

**Purpose:** Wrapper for Stripe API operations.

**Implementation Requirements:**
```python
import stripe
from typing import Dict, Optional
from decimal import Decimal

from src.config import settings

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    """
    Stripe API wrapper.
    
    Why wrapper:
    - Centralized Stripe operations
    - Error handling
    - Testing isolation
    - Type safety
    """
    
    # Stripe Price IDs (created in Stripe Dashboard)
    PRICE_IDS = {
        'single_sport_monthly': 'price_xxxxx',
        'single_sport_yearly': 'price_xxxxx',
        'all_sports_monthly': 'price_xxxxx',
        'all_sports_yearly': 'price_xxxxx',
        'elite_monthly': 'price_xxxxx',
        'elite_yearly': 'price_xxxxx',
    }
    
    def create_customer(self, email: str, user_id: str) -> Dict:
        """
        Create Stripe customer.
        
        Args:
            email: User email
            user_id: Our internal user ID
            
        Returns:
            Stripe customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={'user_id': str(user_id)},
            )
            return customer
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create customer: {str(e)}")
    
    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        sport: Optional[str] = None,
        success_url: str = None,
        cancel_url: str = None,
    ) -> Dict:
        """
        Create Stripe Checkout session.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            sport: Sport selection (if single sport tier)
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
            
        Returns:
            Checkout session object with session.url
        """
        try:
            metadata = {}
            if sport:
                metadata['sport'] = sport
            
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode='subscription',
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                subscription_data={
                    'metadata': metadata,
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
            
            return session
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Dict:
        """
        Create billing portal session (self-service).
        
        Allows customers to:
        - Update payment method
        - View invoices
        - Cancel subscription
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create portal session: {str(e)}")
    
    def get_subscription(self, subscription_id: str) -> Dict:
        """Get subscription details from Stripe"""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to get subscription: {str(e)}")
    
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Dict:
        """
        Cancel subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at period end. If False, cancel immediately.
        """
        try:
            if at_period_end:
                return stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                return stripe.Subscription.delete(subscription_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to cancel subscription: {str(e)}")
    
    def update_subscription(
        self,
        subscription_id: str,
        new_price_id: str,
        proration_behavior: str = 'create_prorations'
    ) -> Dict:
        """
        Update subscription (upgrade/downgrade).
        
        Args:
            subscription_id: Stripe subscription ID
            new_price_id: New Stripe price ID
            proration_behavior: 'create_prorations', 'none', 'always_invoice'
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior=proration_behavior,
            )
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to update subscription: {str(e)}")
```

**Tests Required:**
- Test create_customer()
- Test create_checkout_session()
- Test create_billing_portal_session()
- Test cancel_subscription()
- Test update_subscription()
- Mock Stripe API for testing

**Acceptance Criteria:**
- [ ] All Stripe operations wrapped
- [ ] Error handling works
- [ ] Metadata passed correctly
- [ ] Tests use mocks (not real Stripe)

---

#### 12.2.2 `src/services/subscription_manager.py`

**Purpose:** Business logic for subscription management.

**Implementation Requirements:**
```python
from typing import Optional
from datetime import datetime
from uuid import UUID

from src.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from src.models.customer import StripeCustomer
from src.services.stripe_service import StripeService
from src.database import get_db_session

class SubscriptionManager:
    """
    High-level subscription management.
    
    Why separate from StripeService:
    - StripeService = API wrapper
    - SubscriptionManager = business logic
    - Easier to test business rules
    """
    
    def __init__(self):
        self.stripe = StripeService()
    
    def get_or_create_customer(self, user_id: UUID, email: str) -> StripeCustomer:
        """Get existing customer or create new one"""
        with get_db_session() as db:
            customer = db.query(StripeCustomer).filter(
                StripeCustomer.user_id == user_id
            ).first()
            
            if customer:
                return customer
            
            # Create in Stripe
            stripe_customer = self.stripe.create_customer(email, user_id)
            
            # Save to DB
            customer = StripeCustomer(
                user_id=user_id,
                stripe_customer_id=stripe_customer['id'],
                stripe_email=email,
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            
            return customer
    
    def create_subscription_from_webhook(self, stripe_subscription: dict):
        """
        Create subscription record from Stripe webhook.
        
        Called when subscription.created webhook fires.
        """
        with get_db_session() as db:
            # Find customer
            customer = db.query(StripeCustomer).filter(
                StripeCustomer.stripe_customer_id == stripe_subscription['customer']
            ).first()
            
            if not customer:
                raise ValueError(f"Customer not found: {stripe_subscription['customer']}")
            
            # Determine tier from price_id
            price_id = stripe_subscription['items']['data'][0]['price']['id']
            tier, interval = self._map_price_to_tier(price_id)
            
            # Get sport from metadata (if single sport)
            sport = stripe_subscription.get('metadata', {}).get('sport')
            
            # Create subscription
            subscription = Subscription(
                customer_id=customer.id,
                stripe_subscription_id=stripe_subscription['id'],
                stripe_price_id=price_id,
                tier=tier,
                status=stripe_subscription['status'],
                sport=sport,
                amount=stripe_subscription['items']['data'][0]['price']['unit_amount'] / 100,
                interval=interval,
                current_period_start=datetime.fromtimestamp(stripe_subscription['current_period_start']),
                current_period_end=datetime.fromtimestamp(stripe_subscription['current_period_end']),
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            return subscription
    
    def update_subscription_from_webhook(self, stripe_subscription: dict):
        """
        Update subscription from Stripe webhook.
        
        Called when subscription.updated webhook fires.
        """
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_subscription['id']
            ).first()
            
            if not subscription:
                # Create if doesn't exist
                return self.create_subscription_from_webhook(stripe_subscription)
            
            # Update fields
            subscription.status = stripe_subscription['status']
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription['current_period_start'])
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription['current_period_end'])
            subscription.cancel_at_period_end = stripe_subscription.get('cancel_at_period_end', False)
            
            if stripe_subscription.get('canceled_at'):
                subscription.canceled_at = datetime.fromtimestamp(stripe_subscription['canceled_at'])
            
            db.commit()
            db.refresh(subscription)
            
            return subscription
    
    def cancel_subscription_from_webhook(self, stripe_subscription: dict):
        """Handle subscription cancellation"""
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_subscription['id']
            ).first()
            
            if subscription:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.utcnow()
                db.commit()
    
    def get_active_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """Get user's active subscription"""
        with get_db_session() as db:
            customer = db.query(StripeCustomer).filter(
                StripeCustomer.user_id == user_id
            ).first()
            
            if not customer:
                return None
            
            subscription = db.query(Subscription).filter(
                Subscription.customer_id == customer.id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
            ).first()
            
            return subscription
    
    def _map_price_to_tier(self, price_id: str) -> tuple:
        """Map Stripe price ID to tier and interval"""
        mapping = {
            StripeService.PRICE_IDS['single_sport_monthly']: (SubscriptionTier.SINGLE_SPORT, 'month'),
            StripeService.PRICE_IDS['single_sport_yearly']: (SubscriptionTier.SINGLE_SPORT, 'year'),
            StripeService.PRICE_IDS['all_sports_monthly']: (SubscriptionTier.ALL_SPORTS, 'month'),
            StripeService.PRICE_IDS['all_sports_yearly']: (SubscriptionTier.ALL_SPORTS, 'year'),
            StripeService.PRICE_IDS['elite_monthly']: (SubscriptionTier.ELITE, 'month'),
            StripeService.PRICE_IDS['elite_yearly']: (SubscriptionTier.ELITE, 'year'),
        }
        
        return mapping.get(price_id, (SubscriptionTier.FREE, 'month'))
```

**Tests Required:**
- Test get_or_create_customer()
- Test create_subscription_from_webhook()
- Test update_subscription_from_webhook()
- Test get_active_subscription()
- Test tier mapping

**Acceptance Criteria:**
- [ ] Customer creation works
- [ ] Webhook handling correct
- [ ] Active subscription retrieval works
- [ ] Tier mapping accurate

---

## Phase 12.3: API Endpoints

### Files to Create

#### 12.3.1 `src/api/checkout.py`

**Purpose:** Checkout and subscription creation endpoints.

**Implementation Requirements:**
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.services.stripe_service import StripeService
from src.services.subscription_manager import SubscriptionManager
from src.api.dependencies import get_current_user
from src.config import settings

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

class CheckoutRequest(BaseModel):
    tier: str  # 'single_sport', 'all_sports', 'elite'
    interval: str  # 'month' or 'year'
    sport: Optional[str] = None  # Required if tier='single_sport'

@router.post("/create-session")
def create_checkout_session(
    request: CheckoutRequest,
    user = Depends(get_current_user)
):
    """
    Create Stripe Checkout session.
    
    Returns:
        {
            'session_id': 'cs_xxxxx',
            'url': 'https://checkout.stripe.com/...'
        }
    """
    # Validate
    if request.tier == 'single_sport' and not request.sport:
        raise HTTPException(status_code=400, detail="Sport required for single sport tier")
    
    if request.sport and request.sport not in ['NFL', 'NBA', 'NHL']:
        raise HTTPException(status_code=400, detail="Invalid sport")
    
    # Get or create customer
    manager = SubscriptionManager()
    customer = manager.get_or_create_customer(user.id, user.email)
    
    # Get price ID
    stripe_service = StripeService()
    price_key = f"{request.tier}_{request.interval}"
    price_id = stripe_service.PRICE_IDS.get(price_key)
    
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid tier/interval combination")
    
    # Create checkout session
    session = stripe_service.create_checkout_session(
        customer_id=customer.stripe_customer_id,
        price_id=price_id,
        sport=request.sport,
        success_url=f"{settings.FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/pricing",
    )
    
    return {
        'session_id': session['id'],
        'url': session['url'],
    }

@router.get("/success")
def checkout_success(session_id: str):
    """
    Handle successful checkout.
    
    Called after user completes payment.
    Note: Actual subscription creation happens via webhook.
    """
    # Could fetch session details if needed
    return {
        'success': True,
        'message': 'Subscription activated! Webhook will sync your account.',
    }
```

**Tests Required:**
- Test create_checkout_session()
- Test tier validation
- Test sport validation
- Test price ID lookup

**Acceptance Criteria:**
- [ ] Checkout session created
- [ ] Validation works
- [ ] Success redirect correct

---

#### 12.3.2 `src/api/webhooks.py`

**Purpose:** Stripe webhook handlers.

**Implementation Requirements:**
```python
from fastapi import APIRouter, Request, HTTPException
import stripe
from stripe.error import SignatureVerificationError

from src.config import settings
from src.services.subscription_manager import SubscriptionManager
from src.models.payment_history import PaymentHistory
from src.models.customer import StripeCustomer
from src.database import get_db_session

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks.
    
    Events handled:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle event
    manager = SubscriptionManager()
    
    if event['type'] == 'customer.subscription.created':
        manager.create_subscription_from_webhook(event['data']['object'])
    
    elif event['type'] == 'customer.subscription.updated':
        manager.update_subscription_from_webhook(event['data']['object'])
    
    elif event['type'] == 'customer.subscription.deleted':
        manager.cancel_subscription_from_webhook(event['data']['object'])
    
    elif event['type'] == 'invoice.payment_succeeded':
        _handle_payment_succeeded(event['data']['object'])
    
    elif event['type'] == 'invoice.payment_failed':
        _handle_payment_failed(event['data']['object'])
    
    return {'status': 'success'}

def _handle_payment_succeeded(invoice: dict):
    """Record successful payment"""
    with get_db_session() as db:
        # Find customer
        customer = db.query(StripeCustomer).filter(
            StripeCustomer.stripe_customer_id == invoice['customer']
        ).first()
        
        if not customer:
            return
        
        # Create payment record
        payment = PaymentHistory(
            customer_id=customer.id,
            stripe_payment_intent_id=invoice['payment_intent'],
            stripe_charge_id=invoice.get('charge'),
            amount=invoice['amount_paid'] / 100,
            currency=invoice['currency'],
            status='succeeded',
            description=invoice.get('description'),
            receipt_url=invoice.get('hosted_invoice_url'),
            paid_at=datetime.fromtimestamp(invoice['status_transitions']['paid_at']) if invoice.get('status_transitions', {}).get('paid_at') else None,
        )
        
        db.add(payment)
        db.commit()

def _handle_payment_failed(invoice: dict):
    """Handle failed payment"""
    with get_db_session() as db:
        customer = db.query(StripeCustomer).filter(
            StripeCustomer.stripe_customer_id == invoice['customer']
        ).first()
        
        if not customer:
            return
        
        # Create failed payment record
        payment = PaymentHistory(
            customer_id=customer.id,
            stripe_payment_intent_id=invoice['payment_intent'],
            amount=invoice['amount_due'] / 100,
            currency=invoice['currency'],
            status='failed',
            description=invoice.get('description'),
        )
        
        db.add(payment)
        db.commit()
        
        # TODO: Send email to user about failed payment
```

**Tests Required:**
- Test webhook signature verification
- Test subscription.created handling
- Test subscription.updated handling
- Test payment_succeeded handling
- Test payment_failed handling

**Acceptance Criteria:**
- [ ] Webhooks verified correctly
- [ ] All events handled
- [ ] Payment history recorded
- [ ] Database updated properly

---

## Phase 12.4: Access Control Middleware

### Files to Create

#### 12.4.1 `src/middleware/subscription_required.py`

**Purpose:** Enforce subscription requirements on API endpoints.

**Implementation Requirements:**
```python
from fastapi import HTTPException, Depends
from typing import Optional

from src.services.subscription_manager import SubscriptionManager
from src.models.subscription import SubscriptionTier

def require_subscription(
    tier: Optional[SubscriptionTier] = None,
    sport: Optional[str] = None
):
    """
    Dependency to enforce subscription requirements.
    
    Usage:
        @router.get("/patterns", dependencies=[Depends(require_subscription(tier=SubscriptionTier.SINGLE_SPORT, sport="NFL"))])
    """
    def dependency(user = Depends(get_current_user)):
        manager = SubscriptionManager()
        subscription = manager.get_active_subscription(user.id)
        
        # No subscription = free tier only
        if not subscription:
            raise HTTPException(
                status_code=402,
                detail="Subscription required. Upgrade at /pricing"
            )
        
        # Check tier
        if tier and subscription.tier != tier:
            tier_order = {
                SubscriptionTier.FREE: 0,
                SubscriptionTier.SINGLE_SPORT: 1,
                SubscriptionTier.ALL_SPORTS: 2,
                SubscriptionTier.ELITE: 3,
            }
            
            if tier_order.get(subscription.tier, 0) < tier_order.get(tier, 0):
                raise HTTPException(
                    status_code=402,
                    detail=f"{tier} tier required. Upgrade at /pricing"
                )
        
        # Check sport access
        if sport and not subscription.can_access_sport(sport):
            raise HTTPException(
                status_code=403,
                detail=f"Your subscription doesn't include {sport}. Upgrade to All Sports at /pricing"
            )
        
        return subscription
    
    return dependency

def require_premium():
    """Shortcut for requiring any paid tier"""
    return require_subscription(tier=SubscriptionTier.SINGLE_SPORT)

def require_elite():
    """Shortcut for requiring elite tier"""
    return require_subscription(tier=SubscriptionTier.ELITE)
```

**Tests Required:**
- Test subscription enforcement
- Test tier validation
- Test sport access validation
- Test error messages

**Acceptance Criteria:**
- [ ] Blocks free users from paid features
- [ ] Validates tier correctly
- [ ] Validates sport access
- [ ] Clear error messages

---

## Phase 12.5: Frontend Integration

### Files to Create

#### 12.5.1 `frontend/src/components/PricingTable.tsx`

**Purpose:** Pricing page with Stripe Checkout.

**Implementation Requirements:**
```typescript
import React, { useState } from 'react';
import api from '../services/api';

interface PricingTier {
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
  tier_key: string;
  sport_selection?: boolean;
}

const tiers: PricingTier[] = [
  {
    name: 'Single Sport',
    price_monthly: 14.99,
    price_yearly: 119,
    tier_key: 'single_sport',
    sport_selection: true,
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
    name: 'All Sports',
    price_monthly: 29.99,
    price_yearly: 249,
    tier_key: 'all_sports',
    features: [
      'Access all sports',
      'Everything in Single Sport',
      'Cross-sport insights',
      'Switch sports anytime',
    ],
  },
  {
    name: 'Elite',
    price_monthly: 49.99,
    price_yearly: 399,
    tier_key: 'elite',
    features: [
      'Everything in All Sports',
      'Historical backtesting',
      'API access',
      'Advanced analytics',
      'Priority support',
      'Early access',
    ],
  },
];

const PricingTable: React.FC = () => {
  const [interval, setInterval] = useState<'month' | 'year'>('month');
  const [selectedSport, setSelectedSport] = useState<string>('NFL');
  const [loading, setLoading] = useState<string | null>(null);
  
  const handleSubscribe = async (tier: PricingTier) => {
    setLoading(tier.tier_key);
    
    try {
      const response = await api.post('/checkout/create-session', {
        tier: tier.tier_key,
        interval: interval,
        sport: tier.sport_selection ? selectedSport : null,
      });
      
      // Redirect to Stripe Checkout
      window.location.href = response.data.url;
    } catch (error) {
      console.error('Checkout error:', error);
      alert('Failed to start checkout. Please try again.');
    } finally {
      setLoading(null);
    }
  };
  
  return (
    <div className="container mx-auto p-8">
      <h1 className="text-4xl font-bold text-center mb-8">
        Choose Your Plan
      </h1>
      
      {/* Interval Toggle */}
      <div className="flex justify-center gap-4 mb-12">
        <button
          onClick={() => setInterval('month')}
          className={`px-6 py-3 rounded-lg ${
            interval === 'month'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700'
          }`}
        >
          Monthly
        </button>
        <button
          onClick={() => setInterval('year')}
          className={`px-6 py-3 rounded-lg ${
            interval === 'year'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700'
          }`}
        >
          Yearly <span className="text-sm">(Save 33%)</span>
        </button>
      </div>
      
      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {tiers.map((tier) => (
          <div
            key={tier.name}
            className="border-2 rounded-lg p-6 hover:shadow-lg transition"
          >
            <h3 className="text-2xl font-bold mb-4">{tier.name}</h3>
            
            <div className="mb-6">
              <span className="text-4xl font-bold">
                ${interval === 'month' ? tier.price_monthly : tier.price_yearly}
              </span>
              <span className="text-gray-600">
                /{interval === 'month' ? 'mo' : 'yr'}
              </span>
            </div>
            
            {/* Sport Selection */}
            {tier.sport_selection && (
              <div className="mb-4">
                <label className="block text-sm font-semibold mb-2">
                  Choose Sport:
                </label>
                <select
                  value={selectedSport}
                  onChange={(e) => setSelectedSport(e.target.value)}
                  className="w-full border rounded p-2"
                >
                  <option value="NFL">NFL</option>
                  <option value="NBA">NBA</option>
                  <option value="NHL">NHL</option>
                </select>
              </div>
            )}
            
            {/* Features */}
            <ul className="mb-6 space-y-2">
              {tier.features.map((feature, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span className="text-sm">{feature}</span>
                </li>
              ))}
            </ul>
            
            {/* Subscribe Button */}
            <button
              onClick={() => handleSubscribe(tier)}
              disabled={loading === tier.tier_key}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading === tier.tier_key ? 'Loading...' : 'Subscribe'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PricingTable;
```

**Tests Required:**
- Test pricing table rendering
- Test interval toggle
- Test sport selection
- Test checkout flow

**Acceptance Criteria:**
- [ ] Pricing displays correctly
- [ ] Interval toggle works
- [ ] Sport selection works
- [ ] Redirects to Stripe Checkout

---

## Phase 12 Deployment Checklist

**Before going live:**

### Stripe Setup
- [ ] Create Stripe account
- [ ] Create products & prices in Stripe Dashboard
- [ ] Copy price IDs to StripeService.PRICE_IDS
- [ ] Set up webhook endpoint (https://your-api.com/api/webhooks/stripe)
- [ ] Configure webhook events (subscription.*, invoice.*)
- [ ] Get API keys (publishable & secret)
- [ ] Get webhook signing secret

### Environment Variables
- [ ] STRIPE_SECRET_KEY=sk_live_...
- [ ] STRIPE_PUBLISHABLE_KEY=pk_live_...
- [ ] STRIPE_WEBHOOK_SECRET=whsec_...
- [ ] FRONTEND_URL=https://fantasyiq.io

### Testing
- [ ] Test checkout flow end-to-end
- [ ] Test webhook handling
- [ ] Test subscription upgrades
- [ ] Test subscription cancellations
- [ ] Test payment failures
- [ ] Test access control middleware

### Legal
- [ ] Terms of Service
- [ ] Privacy Policy
- [ ] Refund Policy
- [ ] Update Stripe account details

---

## Revenue Tracking

**Key Metrics Dashboard:**
```python
@router.get("/admin/revenue")
def get_revenue_metrics():
    """Admin endpoint for revenue tracking"""
    with get_db_session() as db:
        # MRR (Monthly Recurring Revenue)
        active_subs = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).all()
        
        mrr = sum(
            float(sub.amount) if sub.interval == 'month'
            else float(sub.amount) / 12
            for sub in active_subs
        )
        
        # Tier breakdown
        tier_counts = {}
        for tier in SubscriptionTier:
            count = sum(1 for sub in active_subs if sub.tier == tier)
            tier_counts[tier] = count
        
        # Total revenue (all-time)
        total_revenue = db.query(func.sum(PaymentHistory.amount)).filter(
            PaymentHistory.status == 'succeeded'
        ).scalar() or 0
        
        return {
            'mrr': round(mrr, 2),
            'arr': round(mrr * 12, 2),
            'active_subscriptions': len(active_subs),
            'tier_breakdown': tier_counts,
            'lifetime_revenue': float(total_revenue),
        }
```

---

**Phase 12 complete gives you a full subscription platform. Ready to make money.**
