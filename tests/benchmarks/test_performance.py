"""
Performance benchmarks for DFS Behavioral Parser.

Performance targets:
- CSV parsing: <500ms for 1000 entries
- Persona detection: <100ms
- Weight mapping: <50ms
- End-to-end pipeline: <1s
"""

import pytest
import time
from io import StringIO
from datetime import datetime, timedelta
from decimal import Decimal

from src.parsers.draftkings_parser import DraftKingsParser
from src.classifiers.contest_type_classifier import ContestTypeClassifier
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.persona_detector import PersonaDetector
from src.scoring.weight_mapper import WeightMapper
from src.models.dfs_entry import DFSEntry
from src.models.behavioral_metrics import BehavioralMetrics


def generate_sample_entries(count: int) -> list:
    """Generate sample DFSEntry objects for benchmarking."""
    base_date = datetime(2024, 1, 1)
    sports = ["NFL", "NBA", "MLB", "NHL", "PGA"]
    contest_types = ["GPP", "CASH", "H2H", "MULTI"]

    entries = []
    for i in range(count):
        entries.append(DFSEntry(
            entry_id=str(i),
            date=base_date + timedelta(days=i % 365),
            sport=sports[i % len(sports)],
            contest_type=contest_types[i % len(contest_types)],
            entry_fee=Decimal(str((i % 100) + 1)),
            winnings=Decimal(str((i % 50) * 2)),
            points=Decimal(str(100 + (i % 200))),
            source="DK",
            contest_name=f"Contest {i}",
        ))
    return entries


def generate_csv_string(count: int) -> StringIO:
    """Generate sample CSV data for benchmarking."""
    header = "Entry ID,Contest Name,Entry Fee,Winnings,Points,Sport,Date Entered\n"
    rows = []
    sports = ["NFL", "NBA", "MLB", "NHL", "PGA"]

    for i in range(count):
        sport = sports[i % len(sports)]
        contest = f"{sport} $20K GPP" if i % 3 == 0 else f"{sport} 50/50"
        fee = (i % 100) + 1
        winnings = (i % 50) * 2
        date = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
        rows.append(f"{i},{contest},${fee}.00,${winnings}.00,{100 + i % 200},{sport},{date}\n")

    return StringIO(header + "".join(rows))


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_csv_parsing_1000_entries(self, benchmark):
        """CSV parsing: <500ms for 1000 entries."""
        csv_data = generate_csv_string(1000)

        def parse_csv():
            csv_data.seek(0)
            parser = DraftKingsParser()
            return parser.parse(csv_data)

        result = benchmark(parse_csv)
        assert len(result) == 1000

        # Verify performance target
        stats = benchmark.stats
        assert stats.stats.mean < 0.5, f"Mean time {stats.stats.mean:.3f}s exceeds 500ms"

    def test_classification_1000_entries(self, benchmark):
        """Contest classification: <200ms for 1000 entries."""
        entries = generate_sample_entries(1000)
        # Set contest_type to UNKNOWN to force classification
        for e in entries:
            e.contest_type = "UNKNOWN"
            e.contest_name = "NFL $20K GPP" if entries.index(e) % 2 == 0 else "NBA 50/50"

        classifier = ContestTypeClassifier()

        def classify():
            return classifier.classify_entries(entries)

        result = benchmark(classify)
        assert len(result) == 1000

    def test_behavioral_scoring_1000_entries(self, benchmark):
        """Behavioral scoring: <300ms for 1000 entries."""
        entries = generate_sample_entries(1000)
        scorer = BehavioralScorer()

        def score():
            return scorer.calculate_metrics(entries)

        result = benchmark(score)
        assert result.total_entries == 1000

    def test_persona_detection_performance(self, benchmark):
        """Persona detection: <100ms."""
        entries = generate_sample_entries(100)
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(entries)
        detector = PersonaDetector()

        def detect():
            return detector.score_personas(metrics)

        result = benchmark(detect)
        assert result.bettor is not None

        stats = benchmark.stats
        assert stats.stats.mean < 0.1, f"Mean time {stats.stats.mean:.3f}s exceeds 100ms"

    def test_weight_mapping_performance(self, benchmark):
        """Weight mapping: <50ms."""
        entries = generate_sample_entries(100)
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(entries)
        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)
        mapper = WeightMapper()

        def map_weights():
            return mapper.calculate_weights(persona_score)

        result = benchmark(map_weights)
        assert result.line_movement > Decimal('0')

        stats = benchmark.stats
        assert stats.stats.mean < 0.05, f"Mean time {stats.stats.mean:.3f}s exceeds 50ms"

    def test_end_to_end_pipeline_performance(self, benchmark):
        """End-to-end pipeline: <1s for 1000 entries."""
        csv_data = generate_csv_string(1000)

        def pipeline():
            csv_data.seek(0)

            # Parse
            parser = DraftKingsParser()
            entries = parser.parse(csv_data)

            # Classify
            classifier = ContestTypeClassifier()
            classified = classifier.classify_entries(entries)

            # Score
            scorer = BehavioralScorer()
            metrics = scorer.calculate_metrics(classified)

            # Detect personas
            detector = PersonaDetector()
            persona_score = detector.score_personas(metrics)

            # Map weights
            mapper = WeightMapper()
            weights = mapper.calculate_weights(persona_score)

            return weights

        result = benchmark(pipeline)
        assert result.line_movement > Decimal('0')

        stats = benchmark.stats
        assert stats.stats.mean < 1.0, f"Mean time {stats.stats.mean:.3f}s exceeds 1s"


class TestPerformanceWithoutBenchmark:
    """Performance tests without pytest-benchmark (for CI compatibility)."""

    def test_csv_parsing_time(self):
        """CSV parsing time test."""
        csv_data = generate_csv_string(1000)

        start = time.time()
        parser = DraftKingsParser()
        entries = parser.parse(csv_data)
        elapsed = time.time() - start

        assert len(entries) == 1000
        assert elapsed < 0.5, f"CSV parsing took {elapsed:.3f}s, expected < 500ms"

    def test_end_to_end_time(self):
        """End-to-end pipeline time test."""
        csv_data = generate_csv_string(1000)

        start = time.time()

        parser = DraftKingsParser()
        entries = parser.parse(csv_data)

        classifier = ContestTypeClassifier()
        classified = classifier.classify_entries(entries)

        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(classified)

        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        elapsed = time.time() - start

        assert weights.line_movement > Decimal('0')
        assert elapsed < 1.0, f"Pipeline took {elapsed:.3f}s, expected < 1s"
