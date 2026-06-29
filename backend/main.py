import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting LabelX backend…")
    # Pre-warm Qdrant collection
    try:
        from services.qdrant_service import ensure_collection
        await ensure_collection()
        logger.info("Qdrant collection ready.")
    except Exception as e:
        logger.warning(f"Qdrant init warning (non-fatal): {e}")

    # Test Redis
    try:
        from services.redis_service import ping_redis
        ok = await ping_redis()
        logger.info(f"Redis ping: {'OK' if ok else 'FAILED'}")
    except Exception as e:
        logger.warning(f"Redis init warning (non-fatal): {e}")

    yield
    logger.info("LabelX backend shutting down.")


app = FastAPI(
    title="LabelX — Food Safety Analyzer API",
    version="1.0.0",
    description="AI-powered food label analysis with multi-agent LangGraph workflow.",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
frontend_url = os.getenv("FRONTEND_URL", "")
if frontend_url:
    _origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────

from routes.analyze import router as analyze_router
from routes.profile import router as profile_router
from routes.history import router as history_router

app.include_router(analyze_router, prefix="/api", tags=["Analysis"])
app.include_router(profile_router, prefix="/api", tags=["Profile"])
app.include_router(history_router, prefix="/api", tags=["History"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "LabelX Backend",
        "version": "1.0.0",
    }
