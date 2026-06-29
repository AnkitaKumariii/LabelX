"""
POST /api/analyze — Runs the LangGraph multi-agent workflow and streams progress
via Server-Sent Events.

Accepts JSON body with profile_id + ingredients (list or raw_text for OCR).
Also accepts multipart/form-data with an image file for OCR.
"""
import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse

from models.schemas import AnalyzeRequest
from services import redis_service
from services.ocr_service import extract_text_from_image
from services.gemini_service import parse_ingredients_from_text
from graph import graph

logger = logging.getLogger(__name__)
router = APIRouter()


# ── JSON body endpoint ─────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """Accepts JSON with profile_id + ingredients list or raw_text."""
    profile = await redis_service.get_profile(request.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please set up your profile first.")

    ingredients = request.ingredients or []
    if request.raw_text and not ingredients:
        ingredients = await parse_ingredients_from_text(request.raw_text)

    if not ingredients:
        raise HTTPException(status_code=400, detail="No ingredients provided.")

    return _stream_analysis(ingredients, profile, request.profile_id)


# ── Multipart (image upload) endpoint ─────────────────────────────────────────

@router.post("/analyze/image")
async def analyze_image(
    profile_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Accepts an image file; runs OCR then analysis."""
    profile = await redis_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    image_bytes = await file.read()
    try:
        raw_text = await extract_text_from_image(image_bytes)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from image. Try a clearer photo.")

    ingredients = await parse_ingredients_from_text(raw_text)
    if not ingredients:
        raise HTTPException(status_code=422, detail="No ingredients found in the extracted text.")

    return _stream_analysis(ingredients, profile, profile_id)


# ── Shared streaming helper ────────────────────────────────────────────────────

def _stream_analysis(ingredients: List[str], profile: dict, profile_id: str) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()
    analysis_id = str(uuid.uuid4())

    async def run_workflow():
        initial_state = {
            "ingredients": ingredients,
            "user_profile": profile,
            "research_results": [],
            "report": None,
            "score": None,
            "feedback": None,
            "retry_count": 0,
            "status_updates": [],
            "validated": False,
            "error": None,
            "event_queue": queue,
        }
        try:
            final_state = await graph.ainvoke(initial_state)
            report = final_state.get("report") or {}
            score = final_state.get("score") or report.get("summary", {}).get("health_score", 0)

            # Save to history
            history_entry = {
                "analysis_id": analysis_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "health_score": score,
                "ingredient_count": len(ingredients),
                "summary_snippet": report.get("summary", {}).get("personalized_summary", "")[:200],
                "report": report,
            }
            await redis_service.save_analysis(profile_id, history_entry)

            await queue.put({
                "type": "complete",
                "analysis_id": analysis_id,
                "report": report,
                "score": score,
                "progress": 100,
            })
        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            await queue.put({"type": "error", "message": str(e)})
        finally:
            await queue.put(None)   # Sentinel — close the stream

    asyncio.create_task(run_workflow())

    async def event_generator():
        yield f"data: {json.dumps({'type': 'connected', 'analysis_id': analysis_id})}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'timeout', 'message': 'Analysis timed out'})}\n\n"
                break
            if event is None:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
