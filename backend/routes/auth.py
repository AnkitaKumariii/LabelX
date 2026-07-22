import os
import asyncio
from fastapi import APIRouter, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests
from models.schemas import GoogleAuthRequest, UserProfileResponse
from services import redis_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("VITE_GOOGLE_CLIENT_ID")

@router.post("/auth/google", response_model=UserProfileResponse)
async def google_auth(request: GoogleAuthRequest):
    """Verify Google token and return or create the user profile in Redis."""
    try:
        # Verify the token asynchronously in worker thread to prevent blocking FastAPI event loop
        if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_ID != "YOUR_GOOGLE_CLIENT_ID_HERE":
            idinfo = await asyncio.to_thread(
                id_token.verify_oauth2_token, request.token, requests.Request(), GOOGLE_CLIENT_ID
            )
        else:
            # Only for local dev if client ID isn't set securely, though google-auth still verifies signature
            idinfo = await asyncio.to_thread(
                id_token.verify_oauth2_token, request.token, requests.Request()
            )

        user_id = idinfo['sub']
        name = idinfo.get('name', 'User')
        email = idinfo.get('email', '')

        # Check if profile exists
        existing_profile = await redis_service.get_profile(user_id)
        
        if existing_profile:
            return UserProfileResponse(**existing_profile)
            
        # Create a new skeleton profile
        new_profile = {
            "profile_id": user_id,
            "name": name,
            "health_conditions": [],
            "allergies": [],
            "expertise_level": "beginner",
        }
        
        await redis_service.save_profile(user_id, new_profile)
        return UserProfileResponse(**new_profile)

    except ValueError as e:
        logger.error(f"Google Token Verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
