"""
DFS Behavioral Parser API

FastAPI wrapper for Railway deployment.
"""

import io
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from src.parsers.platform_detector import detect_platform
from src.parsers.draftkings_parser import DraftKingsParser
from src.parsers.fanduel_parser import FanDuelParser
from src.classifiers.contest_type_classifier import ContestTypeClassifier
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.persona_detector import PersonaDetector
from src.scoring.weight_mapper import WeightMapper

app = FastAPI(
    title="DFS Behavioral Parser",
    description="Parse DraftKings/FanDuel CSV exports to detect user personas and generate pattern weights",
    version="1.0.0",
)


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "dfs-behavioral-parser",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """Alias for health check."""
    return await health_check()


@app.post("/parse")
async def parse_csv(file: UploadFile = File(...)):
    """
    Parse a DraftKings or FanDuel CSV export.

    Returns behavioral metrics, persona scores, and pattern weights.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Read file content
    content = await file.read()

    # Write to temp file for processing
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Step 1: Detect platform
        try:
            platform = detect_platform(tmp_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Step 2: Parse CSV
        if platform == "DRAFTKINGS":
            parser = DraftKingsParser()
        else:
            parser = FanDuelParser()

        entries = parser.parse(tmp_path)

        if not entries:
            raise HTTPException(status_code=400, detail="No valid entries found in CSV")

        # Step 3: Classify contests
        classifier = ContestTypeClassifier()
        classified_entries = classifier.classify_entries(entries)

        # Step 4: Calculate behavioral metrics
        scorer = BehavioralScorer()
        metrics = scorer.calculate_metrics(classified_entries)

        # Step 5: Detect personas
        detector = PersonaDetector()
        persona_score = detector.score_personas(metrics)

        # Step 6: Generate weights
        mapper = WeightMapper()
        weights = mapper.calculate_weights(persona_score)

        # Build response using model_dump (Pydantic v2)
        response = {
            "platform": platform,
            "entries_count": len(entries),
            "date_range": {
                "start": min(e.date for e in entries).isoformat(),
                "end": max(e.date for e in entries).isoformat(),
            },
            "metrics": metrics.model_dump(mode='json'),
            "persona_scores": persona_score.model_dump(mode='json'),
            "pattern_weights": weights.model_dump(mode='json'),
            "warnings": parser.warnings if parser.warnings else None,
        }

        return JSONResponse(content=response)

    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


@app.post("/analyze")
async def analyze_csv(file: UploadFile = File(...)):
    """Alias for /parse endpoint."""
    return await parse_csv(file)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
