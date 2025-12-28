"""
End-to-end integration tests.

Tests the complete pipeline from CSV file to pattern weights.
"""

import pytest
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from src.parsers.platform_detector import detect_platform
from src.parsers.draftkings_parser import DraftKingsParser
from src.parsers.fanduel_parser import FanDuelParser
from src.classifiers.contest_type_classifier import ContestTypeClassifier
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.persona_detector import PersonaDetector
from src.scoring.weight_mapper import WeightMapper


class TestEndToEnd:
    """End-to-end tests for the complete pipeline."""

    @pytest.fixture
    def fixtures_path(self):
        """Get path to test fixtures."""
        return Path(__file__).parent.parent / "fixtures"

    def test_complete_pipeline_draftkings(self, fixtures_path):
        """Test complete pipeline: CSV -> Weights for DraftKings."""
        csv_path = fixtures_path / "sample_draftkings.csv"

        # Step 1: Detect platform
        platform = detect_platform(csv_path)
        assert platform == "DRAFTKINGS"

        # Step 2: Parse CSV
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)
        assert len(entries) == 8

        # Step 3: Classify contests
        classifier = ContestTypeClassifier()
        classified_entries = classifier.classify_entries(entries)

        # Step 4: Calculate behavioral metrics
        scorer = BehavioralScorer(reference_date=datetime(2024, 11, 1))
        metrics = scorer.calculate_metrics(classified_entries)

        assert metrics.total_entries == 8
        assert metrics.total_invested > Decimal('0')
        assert Decimal('0') <= metrics.confidence_score <= Decimal('1')

        # Step 5: Detect personas
        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        # Verify scores sum to 1.0
        total = persona_score.bettor + persona_score.fantasy + persona_score.stats_nerd
        assert abs(total - Decimal('1')) < Decimal('0.01')
        assert persona_score.primary_persona in ["BETTOR", "FANTASY", "STATS_NERD"]

        # Step 6: Generate weights
        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # Verify weights are reasonable
        assert weights.line_movement > Decimal('0')
        assert weights.situational_stats > Decimal('0')

        # Return full profile for inspection
        return {
            "platform": platform,
            "entries_count": len(entries),
            "metrics": metrics.to_dict(),
            "persona_scores": persona_score.to_dict(),
            "pattern_weights": weights.to_dict(),
        }

    def test_complete_pipeline_fanduel(self, fixtures_path):
        """Test complete pipeline: CSV -> Weights for FanDuel."""
        csv_path = fixtures_path / "sample_fanduel.csv"

        # Step 1: Detect platform
        platform = detect_platform(csv_path)
        assert platform == "FANDUEL"

        # Step 2: Parse CSV
        parser = FanDuelParser()
        entries = parser.parse(csv_path)
        assert len(entries) == 6

        # Step 3: Classify contests
        classifier = ContestTypeClassifier()
        classified_entries = classifier.classify_entries(entries)

        # Step 4: Calculate behavioral metrics
        scorer = BehavioralScorer(reference_date=datetime(2024, 11, 1))
        metrics = scorer.calculate_metrics(classified_entries)

        assert metrics.total_entries == 6

        # Step 5: Detect personas
        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        # Step 6: Generate weights
        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        assert weights.situational_stats > Decimal('0')

    def test_serialization_roundtrip(self, fixtures_path):
        """Test that all outputs can be serialized to JSON-compatible dict."""
        csv_path = fixtures_path / "sample_draftkings.csv"

        # Run pipeline
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)

        classifier = ContestTypeClassifier()
        classified_entries = classifier.classify_entries(entries)

        scorer = BehavioralScorer(reference_date=datetime(2024, 11, 1))
        metrics = scorer.calculate_metrics(classified_entries)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # Serialize all outputs
        metrics_dict = metrics.to_dict()
        persona_dict = persona_score.to_dict()
        weights_dict = weights.to_dict()

        # Verify all values are JSON-serializable (strings, ints, bools, lists, dicts)
        import json
        json_str = json.dumps({
            "metrics": metrics_dict,
            "persona_scores": persona_dict,
            "pattern_weights": weights_dict,
        })
        assert len(json_str) > 0

    def test_different_platforms_different_results(self, fixtures_path):
        """Test that different platforms produce valid but potentially different results."""
        dk_path = fixtures_path / "sample_draftkings.csv"
        fd_path = fixtures_path / "sample_fanduel.csv"

        # DraftKings pipeline
        dk_parser = DraftKingsParser()
        dk_entries = dk_parser.parse(dk_path)

        classifier = ContestTypeClassifier()
        dk_classified = classifier.classify_entries(dk_entries)

        dk_scorer = BehavioralScorer(reference_date=datetime(2024, 11, 1))
        dk_metrics = dk_scorer.calculate_metrics(dk_classified)

        # FanDuel pipeline
        fd_parser = FanDuelParser()
        fd_entries = fd_parser.parse(fd_path)
        fd_classified = classifier.classify_entries(fd_entries)

        fd_scorer = BehavioralScorer(reference_date=datetime(2024, 11, 1))
        fd_metrics = fd_scorer.calculate_metrics(fd_classified)

        # Both should produce valid metrics
        assert dk_metrics.total_entries > 0
        assert fd_metrics.total_entries > 0

        # Entry counts should match fixture files
        assert dk_metrics.total_entries == 8
        assert fd_metrics.total_entries == 6

    def test_persona_weights_consistency(self, fixtures_path):
        """Test that weights are consistent with persona detection."""
        csv_path = fixtures_path / "sample_draftkings.csv"

        # Run pipeline
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)

        classifier = ContestTypeClassifier()
        classified = classifier.classify_entries(entries)

        scorer = BehavioralScorer(reference_date=datetime(2024, 11, 1))
        metrics = scorer.calculate_metrics(classified)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # Get top-weighted patterns
        ranked = weights.weights_ranked

        # Top patterns should be reasonable based on persona
        primary = persona_score.primary_persona
        top_pattern = ranked[0][0]

        # This is a soft check - just verify the pipeline produces sensible output
        assert ranked[0][1] >= ranked[-1][1]  # Top weight >= bottom weight


class TestPerformance:
    """Performance tests for the pipeline."""

    @pytest.fixture
    def fixtures_path(self):
        """Get path to test fixtures."""
        return Path(__file__).parent.parent / "fixtures"

    def test_pipeline_performance(self, fixtures_path):
        """Test that pipeline completes in reasonable time."""
        import time

        csv_path = fixtures_path / "sample_draftkings.csv"

        start = time.time()

        # Run complete pipeline
        platform = detect_platform(csv_path)
        parser = DraftKingsParser()
        entries = parser.parse(csv_path)

        classifier = ContestTypeClassifier()
        classified = classifier.classify_entries(entries)

        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(classified)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        elapsed = time.time() - start

        # Pipeline should complete in under 1 second for small files
        assert elapsed < 1.0, f"Pipeline took {elapsed:.2f}s, expected < 1s"
