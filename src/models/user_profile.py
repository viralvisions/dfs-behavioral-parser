"""
UserProfile model - Complete user behavioral profile.

Uses Pydantic v2 for validation. Persists persona for cross-session use.
"""

from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List

from .behavioral_metrics import BehavioralMetrics
from .persona_score import PersonaScore
from .pattern_weights import PatternWeights


class UserProfile(BaseModel):
    """
    Complete user behavioral profile.
    Why: Persist persona for cross-session, cross-app use.
    """
    user_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Source data summary
    total_entries_parsed: int = Field(ge=0)
    date_range_start: datetime
    date_range_end: datetime
    platforms: List[str]  # ["DK", "FD"]

    # Computed metrics
    behavioral_metrics: BehavioralMetrics
    persona_scores: PersonaScore
    pattern_weights: PatternWeights

    # Metadata
    last_csv_upload: datetime
    confidence_score: Decimal = Field(ge=0, le=1)  # 0.0-1.0, data quality indicator

    model_config = {"frozen": False}
