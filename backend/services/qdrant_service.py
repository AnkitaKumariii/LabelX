import os
import logging
from typing import Optional, Dict, Any, List

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "food_additives")
VECTOR_SIZE = 384          # BAAI/bge-small-en-v1.5
CONFIDENCE_THRESHOLD = 0.7

# ── Singletons ─────────────────────────────────────────────────────────────────

_qdrant_client: Optional[AsyncQdrantClient] = None
_embed_model: Optional[TextEmbedding] = None


def get_embed_model() -> TextEmbedding:
    global _embed_model
    if _embed_model is None:
        logger.info("Loading FastEmbed model (BAAI/bge-small-en-v1.5)…")
        _embed_model = TextEmbedding("BAAI/bge-small-en-v1.5")
        logger.info("FastEmbed model loaded.")
    return _embed_model


def get_sync_client() -> QdrantClient:
    """Sync client used only for seeding."""
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )


async def get_qdrant() -> AsyncQdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
    return _qdrant_client


# ── Collection bootstrap ───────────────────────────────────────────────────────

async def ensure_collection() -> None:
    client = await get_qdrant()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if COLLECTION_NAME not in names:
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
    else:
        logger.info(f"Qdrant collection '{COLLECTION_NAME}' already exists.")


# ── Embed helper ───────────────────────────────────────────────────────────────

def embed_text(text: str) -> List[float]:
    model = get_embed_model()
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()

def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = get_embed_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


# ── Search ─────────────────────────────────────────────────────────────────────

async def search_ingredients_batch(ingredient_names: List[str]) -> List[Optional[Dict[str, Any]]]:
    """
    Search Qdrant for the best matching food additives in a single batch request.
    Returns a list of dicts or None for each ingredient if confidence is below 0.
    """
    if not ingredient_names:
        return []

    try:
        client = await get_qdrant()
        query_vectors = embed_texts([name.lower() for name in ingredient_names])
        
        from qdrant_client.models import SearchRequest
        
        requests = [
            SearchRequest(
                vector=vector,
                limit=1,
                score_threshold=0.0
            ) for vector in query_vectors
        ]
        
        batch_results = await client.search_batch(
            collection_name=COLLECTION_NAME,
            requests=requests
        )
        
        parsed_results = []
        for i, results in enumerate(batch_results):
            if not results:
                parsed_results.append(None)
                continue
                
            best = results[0]
            confidence = float(best.score)
            payload = best.payload or {}
            
            parsed_results.append({
                "name": payload.get("name", ingredient_names[i]),
                "aliases": payload.get("aliases", []),
                "safety_rating": payload.get("safety_rating", "other"),
                "health_impact": payload.get("health_impact", "No data."),
                "conditions_affected": payload.get("conditions_affected", []),
                "banned_in": payload.get("banned_in", []),
                "daily_limit_mg": payload.get("daily_limit_mg"),
                "source": "qdrant",
                "confidence": confidence,
            })
            
        return parsed_results
    except Exception as e:
        logger.error(f"Qdrant batch search error: {e}")
        return [None] * len(ingredient_names)

async def search_ingredient(ingredient_name: str) -> Optional[Dict[str, Any]]:
    """
    Search Qdrant for the best matching food additive.
    Returns None if confidence is below threshold.
    """
    try:
        client = await get_qdrant()
        query_vector = embed_text(ingredient_name.lower())
        results = await client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=1,
            score_threshold=0.0,   # fetch best and check ourselves
        )
        if not results:
            return None

        best = results[0]
        confidence = float(best.score)
        payload = best.payload or {}

        return {
            "name": payload.get("name", ingredient_name),
            "aliases": payload.get("aliases", []),
            "safety_rating": payload.get("safety_rating", "other"),
            "health_impact": payload.get("health_impact", "No data."),
            "conditions_affected": payload.get("conditions_affected", []),
            "banned_in": payload.get("banned_in", []),
            "daily_limit_mg": payload.get("daily_limit_mg"),
            "source": "qdrant",
            "confidence": confidence,
        }
    except Exception as e:
        logger.error(f"Qdrant search error for '{ingredient_name}': {e}")
        return None


# ── Upsert (used by seeder) ────────────────────────────────────────────────────

def upsert_ingredient_sync(client: QdrantClient, point_id: int, data: Dict[str, Any]) -> None:
    """Sync upsert used by the seed script."""
    search_text = f"{data['name']} {' '.join(data.get('aliases', []))}"
    vector = embed_text(search_text.lower())
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=data,
            )
        ],
    )
