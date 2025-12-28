#!/usr/bin/env python3
"""
DFS Behavioral Parser Demo

Demonstrates the complete pipeline:
1. Parse CSV (DraftKings/FanDuel)
2. Classify contests
3. Calculate behavioral metrics
4. Detect persona
5. Generate pattern weights

Usage:
    python demo.py [csv_file]
    python demo.py  # Uses sample DraftKings file
"""

import sys
from datetime import datetime
from pathlib import Path

from src.parsers.platform_detector import detect_platform
from src.parsers.draftkings_parser import DraftKingsParser
from src.parsers.fanduel_parser import FanDuelParser
from src.classifiers.contest_type_classifier import ContestTypeClassifier
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.persona_detector import PersonaDetector
from src.scoring.weight_mapper import WeightMapper


def main(csv_path: str = None):
    """Run the demo pipeline."""
    print("=" * 50)
    print("DFS Behavioral Parser Demo")
    print("=" * 50)
    print()

    # Use sample file if none provided
    if csv_path is None:
        csv_path = Path(__file__).parent / "tests" / "fixtures" / "sample_draftkings.csv"
        print(f"Using sample file: {csv_path.name}")
    else:
        csv_path = Path(csv_path)

    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return 1

    # =========================================================================
    # Step 1: Parse CSV
    # =========================================================================
    print()
    print("[1] Parsing CSV...")

    try:
        platform = detect_platform(csv_path)
        print(f"    -> Detected platform: {platform}")

        if platform == "DRAFTKINGS":
            parser = DraftKingsParser()
        else:
            parser = FanDuelParser()

        entries = parser.parse(csv_path)
        print(f"    -> Parsed {len(entries)} entries")

        if entries:
            dates = [e.date for e in entries]
            date_range = f"{min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}"
            print(f"    -> Date range: {date_range}")

        if parser.warnings:
            print(f"    -> Warnings: {len(parser.warnings)}")

    except Exception as e:
        print(f"    Error parsing CSV: {e}")
        return 1

    # =========================================================================
    # Step 2: Classify contests
    # =========================================================================
    print()
    print("[2] Classifying contests...")

    classifier = ContestTypeClassifier()
    classified_entries = classifier.classify_entries(entries)

    # Count by type
    type_counts = {}
    for entry in classified_entries:
        type_counts[entry.contest_type] = type_counts.get(entry.contest_type, 0) + 1

    for contest_type in ["GPP", "CASH", "H2H", "MULTI", "UNKNOWN"]:
        count = type_counts.get(contest_type, 0)
        if count > 0:
            print(f"    -> {contest_type}: {count} entries")

    # =========================================================================
    # Step 3: Calculate behavioral metrics
    # =========================================================================
    print()
    print("[3] Calculating behavioral metrics...")

    scorer = BehavioralScorer()
    metrics = scorer.calculate_metrics(classified_entries)

    print(f"    -> Total invested: ${metrics.total_invested:.2f}")
    print(f"    -> Total winnings: ${metrics.total_winnings:.2f}")
    print(f"    -> Overall ROI: {float(metrics.roi_overall):.1f}%")
    print(f"    -> GPP percentage: {float(metrics.gpp_percentage) * 100:.1f}%")

    diversity_desc = "highly diverse" if float(metrics.sport_diversity) > 0.7 else \
                    "moderately diverse" if float(metrics.sport_diversity) > 0.4 else "focused"
    print(f"    -> Sport diversity: {float(metrics.sport_diversity):.2f} ({diversity_desc})")
    print(f"    -> Confidence score: {float(metrics.confidence_score):.2f}")

    # =========================================================================
    # Step 4: Detect persona
    # =========================================================================
    print()
    print("[4] Detecting personas...")

    detector = PersonaDetector()
    persona_score = detector.score_personas(metrics)

    # Show ranked scores
    ranked = persona_score.scores_ranked
    for i, (persona, score) in enumerate(ranked):
        marker = " (PRIMARY)" if i == 0 else ""
        print(f"    -> {persona}: {float(score) * 100:.1f}%{marker}")

    print(f"    -> Hybrid: {persona_score.is_hybrid}")
    print(f"    -> Confidence: {float(persona_score.confidence):.2f}")

    # =========================================================================
    # Step 5: Generate pattern weights
    # =========================================================================
    print()
    print("[5] Generating pattern weights...")

    mapper = WeightMapper()
    weights = mapper.calculate_weights(persona_score)

    # Show ranked weights
    ranked_weights = weights.weights_ranked
    for pattern_name, weight in ranked_weights:
        print(f"    -> {pattern_name}: {float(weight):.2f}x")

    # =========================================================================
    # Summary
    # =========================================================================
    print()
    print("=" * 50)
    print("Complete! Profile ready for ThirdDownIQ integration")
    print("=" * 50)

    # Output JSON-like summary
    print()
    print("Profile Summary (JSON):")
    print("-" * 30)

    import json
    profile = {
        "platform": platform,
        "entries_count": len(entries),
        "persona_scores": persona_score.to_dict(),
        "pattern_weights": weights.to_dict(),
        "key_metrics": {
            "roi_overall": str(metrics.roi_overall),
            "sport_diversity": str(metrics.sport_diversity),
            "confidence_score": str(metrics.confidence_score),
        }
    }
    print(json.dumps(profile, indent=2))

    return 0


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(csv_file))
