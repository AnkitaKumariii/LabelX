"""
Research Agent — Searches Qdrant for ingredient safety data.
Falls back to Tavily web search if Qdrant confidence < 0.7.
"""
import os
import logging
from typing import List, Dict, Any

from agents.state import AnalysisState, IngredientResearch

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7


async def _emit(queue, event: dict) -> None:
    if queue:
        await queue.put(event)


async def research_node(state: AnalysisState) -> AnalysisState:
    import asyncio
    from services.qdrant_service import search_ingredient
    from services.gemini_service import parse_ingredient_from_web

    queue = state.get("event_queue")
    ingredients: List[str] = state.get("ingredients", [])
    research_results: List[Dict[str, Any]] = []

    await _emit(queue, {
        "type": "agent_start",
        "agent": "Research Agent",
        "message": f"Researching {len(ingredients)} ingredients…",
        "progress": 10,
    })

    # Lazy-import Tavily to avoid errors if API key is missing
    tavily_client = None
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key:
        try:
            from tavily import TavilyClient
            tavily_client = TavilyClient(api_key=tavily_key)
        except Exception as e:
            logger.warning(f"Tavily client init failed: {e}")

    # Process all ingredients concurrently
    async def process_ingredient(idx, ingredient):
        ingredient_lower = ingredient.strip()

        # 1. Try Qdrant semantic search
        result = await search_ingredient(ingredient_lower)

        if result and result.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
            result["source"] = "qdrant"
            logger.info(f"[Research] Qdrant hit: {ingredient} (conf={result['confidence']:.2f})")
            parsed = result
        else:
            # 2. Fallback: Tavily web search
            await _emit(queue, {
                "type": "research_fallback",
                "message": f"Web search fallback for: {ingredient}",
                "ingredient": ingredient,
            })
            logger.info(f"[Research] Tavily fallback for: {ingredient}")

            if tavily_client:
                try:
                    search_resp = await asyncio.to_thread(
                        tavily_client.search,
                        query=f'food additive "{ingredient}" health effects safety',
                        max_results=3,
                        search_depth="basic",
                    )
                    parsed = await parse_ingredient_from_web(
                        ingredient, search_resp.get("results", [])
                    )
                    parsed["source"] = "tavily"
                    parsed["confidence"] = 0.65
                except Exception as e:
                    logger.error(f"Tavily search error for '{ingredient}': {e}")
                    parsed = _unknown(ingredient, "tavily")
            else:
                parsed = _unknown(ingredient, "unknown")

        progress = 10 + int((idx + 1) / len(ingredients) * 40)
        await _emit(queue, {
            "type": "ingredient_researched",
            "ingredient": ingredient,
            "progress": progress,
            "safety_rating": parsed.get("safety_rating", "unknown"),
        })
        return parsed

    tasks = [process_ingredient(idx, ing) for idx, ing in enumerate(ingredients)]
    research_results = await asyncio.gather(*tasks)

    await _emit(queue, {
        "type": "research_done",
        "message": f"Research complete — {len(research_results)} ingredients processed",
        "progress": 50,
    })

    updates = list(state.get("status_updates", []))
    updates.append({
        "type": "research_done",
        "message": "Research complete",
        "count": len(research_results),
    })

    return {**state, "research_results": list(research_results), "status_updates": updates}

def _unknown(name: str, source: str) -> Dict[str, Any]:
    return {
        "name": name,
        "aliases": [],
        "safety_rating": "unknown",
        "health_impact": "No data available.",
        "conditions_affected": [],
        "banned_in": [],
        "daily_limit_mg": None,
        "source": source,
        "confidence": 0.0,
    }
