from fastapi import APIRouter, HTTPException, Query
from typing import List
from models.schemas import HistoryItem
from services import redis_service

router = APIRouter()


@router.get("/history/{profile_id}", response_model=List[HistoryItem])
async def get_history(
    profile_id: str,
    limit: int = Query(default=20, ge=1, le=50),
):
    """Return past analyses for a given profile, most recent first."""
    profile = await redis_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    history = await redis_service.get_history(profile_id, limit=limit)
    return [
        HistoryItem(
            analysis_id=item.get("analysis_id", ""),
            created_at=item.get("created_at", ""),
            health_score=item.get("health_score", 0),
            ingredient_count=item.get("ingredient_count", 0),
            summary_snippet=item.get("summary_snippet", ""),
        )
        for item in history
    ]
