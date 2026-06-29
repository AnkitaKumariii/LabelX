import uuid
from fastapi import APIRouter, HTTPException
from models.schemas import UserProfileRequest, UserProfileResponse
from services import redis_service

router = APIRouter()


@router.post("/profile", response_model=UserProfileResponse, status_code=201)
async def create_profile(request: UserProfileRequest):
    """Create or update a user health profile stored in Redis."""
    profile_id = str(uuid.uuid4())
    profile = {
        "profile_id": profile_id,
        "name": request.name,
        "health_conditions": [c.lower().strip() for c in request.health_conditions],
        "allergies": [a.lower().strip() for a in request.allergies],
        "expertise_level": request.expertise_level,
    }
    await redis_service.save_profile(profile_id, profile)
    return UserProfileResponse(**profile)


@router.put("/profile/{profile_id}", response_model=UserProfileResponse)
async def update_profile(profile_id: str, request: UserProfileRequest):
    """Update an existing profile."""
    existing = await redis_service.get_profile(profile_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found.")
    updated = {
        **existing,
        "name": request.name,
        "health_conditions": [c.lower().strip() for c in request.health_conditions],
        "allergies": [a.lower().strip() for a in request.allergies],
        "expertise_level": request.expertise_level,
    }
    await redis_service.save_profile(profile_id, updated)
    return UserProfileResponse(**updated)


@router.get("/profile/{profile_id}", response_model=UserProfileResponse)
async def get_profile(profile_id: str):
    """Get a user profile by ID."""
    profile = await redis_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return UserProfileResponse(**profile)
