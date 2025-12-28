"""
ProfileStore - PostgreSQL storage for user profiles.

Uses psycopg2 for PostgreSQL connections with connection pooling.
"""

import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

import psycopg2
from psycopg2 import pool

from src.models.user_profile import UserProfile
from src.models.behavioral_metrics import BehavioralMetrics
from src.models.persona_score import PersonaScore
from src.models.pattern_weights import PatternWeights


class ProfileStore:
    """
    PostgreSQL storage for user profiles.
    Why: Persist personas for cross-session, cross-app access.
    """

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize store with database connection.

        Args:
            connection_string: PostgreSQL connection string.
                             Defaults to DATABASE_URL env var.
        """
        self.connection_string = connection_string or os.getenv('DATABASE_URL')
        self._pool: Optional[pool.SimpleConnectionPool] = None

    def _get_connection(self):
        """Get a connection from the pool."""
        if not self._pool:
            self._pool = pool.SimpleConnectionPool(
                1, 10,  # min 1, max 10 connections
                self.connection_string
            )
        return self._pool.getconn()

    def _release_connection(self, conn):
        """Return connection to pool."""
        if self._pool:
            self._pool.putconn(conn)

    def init_schema(self) -> None:
        """Create the user_profiles table if it doesn't exist."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id UUID PRIMARY KEY,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        total_entries_parsed INTEGER NOT NULL,
                        date_range_start TIMESTAMP NOT NULL,
                        date_range_end TIMESTAMP NOT NULL,
                        platforms TEXT[] NOT NULL,
                        behavioral_metrics JSONB NOT NULL,
                        persona_scores JSONB NOT NULL,
                        pattern_weights JSONB NOT NULL,
                        last_csv_upload TIMESTAMP NOT NULL,
                        confidence_score NUMERIC(4,3) NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_user_profiles_updated
                    ON user_profiles(updated_at DESC);
                """)
                conn.commit()
        finally:
            self._release_connection(conn)

    def save_profile(self, profile: UserProfile) -> UUID:
        """
        Save or update a user profile.

        Args:
            profile: UserProfile to save

        Returns:
            user_id of saved profile
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_profiles (
                        user_id, created_at, updated_at,
                        total_entries_parsed, date_range_start, date_range_end,
                        platforms, behavioral_metrics, persona_scores,
                        pattern_weights, last_csv_upload, confidence_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        updated_at = EXCLUDED.updated_at,
                        total_entries_parsed = EXCLUDED.total_entries_parsed,
                        date_range_start = EXCLUDED.date_range_start,
                        date_range_end = EXCLUDED.date_range_end,
                        platforms = EXCLUDED.platforms,
                        behavioral_metrics = EXCLUDED.behavioral_metrics,
                        persona_scores = EXCLUDED.persona_scores,
                        pattern_weights = EXCLUDED.pattern_weights,
                        last_csv_upload = EXCLUDED.last_csv_upload,
                        confidence_score = EXCLUDED.confidence_score
                """, (
                    str(profile.user_id),
                    profile.created_at,
                    profile.updated_at,
                    profile.total_entries_parsed,
                    profile.date_range_start,
                    profile.date_range_end,
                    profile.platforms,
                    json.dumps(profile.behavioral_metrics.model_dump(mode='json')),
                    json.dumps(profile.persona_scores.model_dump(mode='json')),
                    json.dumps(profile.pattern_weights.model_dump(mode='json')),
                    profile.last_csv_upload,
                    float(profile.confidence_score),
                ))
                conn.commit()
                return profile.user_id
        finally:
            self._release_connection(conn)

    def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Retrieve a user profile by ID.

        Args:
            user_id: UUID of profile to retrieve

        Returns:
            UserProfile if found, None otherwise
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, created_at, updated_at,
                           total_entries_parsed, date_range_start, date_range_end,
                           platforms, behavioral_metrics, persona_scores,
                           pattern_weights, last_csv_upload, confidence_score
                    FROM user_profiles
                    WHERE user_id = %s
                """, (str(user_id),))

                row = cur.fetchone()
                if not row:
                    return None

                return UserProfile(
                    user_id=UUID(row[0]),
                    created_at=row[1],
                    updated_at=row[2],
                    total_entries_parsed=row[3],
                    date_range_start=row[4],
                    date_range_end=row[5],
                    platforms=row[6],
                    behavioral_metrics=BehavioralMetrics(**row[7]),
                    persona_scores=PersonaScore(**row[8]),
                    pattern_weights=PatternWeights(**row[9]),
                    last_csv_upload=row[10],
                    confidence_score=Decimal(str(row[11])),
                )
        finally:
            self._release_connection(conn)

    def delete_profile(self, user_id: UUID) -> bool:
        """
        Delete a user profile.

        Args:
            user_id: UUID of profile to delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_profiles WHERE user_id = %s",
                    (str(user_id),)
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            self._release_connection(conn)

    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
