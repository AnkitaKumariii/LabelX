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
    import time
    import asyncio
    from services.qdrant_service import search_ingredients_batch
    from services.gemini_service import parse_ingredient_from_web
    from services.redis_service import get_tavily_cache, set_tavily_cache

    start_time = time.time()
    queue = state.get("event_queue")
    ingredients: List[str] = state.get("ingredients", [])
    research_results: List[Dict[str, Any]] = []

    await _emit(queue, {"stage": "research", "status": "running"})
    await _emit(queue, {
        "type": "agent_start",
        "agent": "Research Agent",
        "message": f"Researching {len(ingredients)} ingredients…",
        "progress": 10,
    })

    # Lazy-import Tavily
    tavily_client = None
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key:
        try:
            from tavily import AsyncTavilyClient
            tavily_client = AsyncTavilyClient(api_key=tavily_key)
        except Exception as e:
            try:
                from tavily import TavilyClient
                tavily_client = TavilyClient(api_key=tavily_key)
            except Exception as e:
                logger.warning(f"Tavily client init failed: {e}")

    # 1. Batch Qdrant Search
    clean_ingredients = [ing.strip() for ing in ingredients]
    batch_results = await search_ingredients_batch(clean_ingredients)
    
    # 2. Process results and prepare fallbacks
    fallback_tasks = []
    
    async def fallback_search(idx: int, ingredient: str):
        # Check Redis Cache
        cached = await get_tavily_cache(ingredient)
        if cached:
            logger.info(f"[Research] Redis cache hit for: {ingredient}")
            parsed = cached
            parsed["source"] = "tavily_cache"
        else:
            # Tavily Fallback
            await _emit(queue, {
                "type": "research_fallback",
                "message": f"Web search fallback for: {ingredient}",
                "ingredient": ingredient,
            })
            logger.info(f"[Research] Tavily fallback for: {ingredient}")

            if tavily_client:
                try:
                    if hasattr(tavily_client, 'search'):
                        # Sync client requires to_thread
                        search_resp = await asyncio.to_thread(
                            tavily_client.search,
                            query=f'food additive "{ingredient}" health effects safety',
                            max_results=3,
                            search_depth="basic",
                        )
                    else:
                        search_resp = await tavily_client.search(
                            query=f'food additive "{ingredient}" health effects safety',
                            max_results=3,
                            search_depth="basic",
                        )
                    parsed = await parse_ingredient_from_web(
                        ingredient, search_resp.get("results", [])
                    )
                    parsed["source"] = "tavily"
                    parsed["confidence"] = 0.65
                    
                    # Cache the result
                    await set_tavily_cache(ingredient, parsed)
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
        return idx, parsed

    # Filter out which ones need fallback
    for idx, (ingredient, qdrant_res) in enumerate(zip(clean_ingredients, batch_results)):
        if qdrant_res and qdrant_res.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
            qdrant_res["source"] = "qdrant"
            logger.info(f"[Research] Qdrant hit: {ingredient} (conf={qdrant_res['confidence']:.2f})")
            research_results.append((idx, qdrant_res))
            
            progress = 10 + int((idx + 1) / len(ingredients) * 40)
            await _emit(queue, {
                "type": "ingredient_researched",
                "ingredient": ingredient,
                "progress": progress,
                "safety_rating": qdrant_res.get("safety_rating", "unknown"),
            })
        else:
            fallback_tasks.append(fallback_search(idx, ingredient))

    # Execute all fallbacks concurrently
    fallback_results = await asyncio.gather(*fallback_tasks)
    
    # Combine and sort results to maintain original order
    all_results = research_results + list(fallback_results)
    all_results.sort(key=lambda x: x[0])
    final_research_results = [res[1] for res in all_results]

    await _emit(queue, {
        "type": "research_done",
        "message": f"Research complete — {len(final_research_results)} ingredients processed",
        "progress": 50,
    })

    updates = list(state.get("status_updates", []))
    updates.append({
        "type": "research_done",
        "message": "Research complete",
        "count": len(final_research_results),
    })

    await _emit(queue, {"stage": "research", "status": "done", "duration_sec": time.time() - start_time})
    return {**state, "research_results": final_research_results, "status_updates": updates}

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
