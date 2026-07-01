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

# ── Rule-Based Classifications ────────────────────────────────────────────────

NON_VEG_RULES = {
    "gelatin": {"reason": "pig/cow bones", "source": "animal"},
    "e441": {"reason": "pig/cow bones (gelatin)", "source": "animal"},
    "carmine": {"reason": "crushed beetles", "source": "animal (insect)"},
    "e120": {"reason": "crushed beetles (carmine)", "source": "animal (insect)"},
    "lard": {"reason": "pig fat", "source": "animal"},
    "isinglass": {"reason": "fish bladder", "source": "animal (fish)"},
    "l-cysteine": {"reason": "duck feathers/human hair", "source": "animal"},
    "e920": {"reason": "duck feathers (l-cysteine)", "source": "animal"},
    "rennet": {"reason": "calf enzyme", "source": "animal"},
    "shellac": {"reason": "insect secretion", "source": "animal (insect)"},
    "e904": {"reason": "insect secretion (shellac)", "source": "animal (insect)"},
    "omega-3": {"reason": "often fish-derived", "source": "animal (fish)"},
    "vitamin d3": {"reason": "sheep wool (lanolin)", "source": "animal (sheep)"},
}

NON_VEGAN_RULES = {
    "casein": {"reason": "milk protein", "source": "animal (dairy)"},
    "whey": {"reason": "milk", "source": "animal (dairy)"},
    "lactose": {"reason": "milk sugar", "source": "animal (dairy)"},
    "egg": {"reason": "egg", "source": "animal (egg)"},
    "albumen": {"reason": "egg white", "source": "animal (egg)"},
    "honey": {"reason": "bee secretion", "source": "animal (insect)"},
    "beeswax": {"reason": "bee secretion", "source": "animal (insect)"},
    "e901": {"reason": "bee secretion (beeswax)", "source": "animal (insect)"},
}

def classify_veg(ingredient_name: str) -> Dict[str, Any]:
    name_lower = ingredient_name.lower().strip()
    
    # Check non-veg
    for key, data in NON_VEG_RULES.items():
        if key in name_lower:
            return {"is_veg": False, "is_vegan": False, "reason": data["reason"], "source": data["source"]}
            
    # Check non-vegan
    for key, data in NON_VEGAN_RULES.items():
        if key in name_lower:
            return {"is_veg": True, "is_vegan": False, "reason": data["reason"], "source": data["source"]}
            
    return {"is_veg": True, "is_vegan": True, "reason": None, "source": "plant/synthetic/mineral"}

def classify_processing(ingredient_name: str) -> str:
    name = ingredient_name.lower().strip()
    
    ultra = ["artificial", "synthetic", "hydrogenated", "color", "red 40", "yellow 5", "blue 1", "e1", "e2", "e3", "e4", "e5", "e6", "e9"]
    processed = ["maltodextrin", "starch", "syrup", "isolate", "refined", "extract", "concentrate", "powder"]
    
    if any(u in name for u in ultra):
        return "ultra_processed"
    if any(p in name for p in processed):
        return "processed"
    if any(r in name for r in ["turmeric", "salt", "sugar", "water", "spice", "oil"]):
        return "raw"
        
    return "minimally_processed"

def get_worst_processing_level(levels: List[str]) -> str:
    if "ultra_processed" in levels: return "ultra_processed"
    if "processed" in levels: return "processed"
    if "minimally_processed" in levels: return "minimally_processed"
    return "raw"


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
                    if isinstance(tavily_client, AsyncTavilyClient):
                        search_resp = await tavily_client.search(
                            query=f'food additive "{ingredient}" health effects safety',
                            max_results=3,
                            search_depth="basic",
                        )
                    else:
                        # Sync client requires to_thread
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
                    
                    # Cache the result
                    await set_tavily_cache(ingredient, parsed)
                except Exception as e:
                    logger.error(f"Tavily search error for '{ingredient}': {e}")
                    parsed = _other(ingredient, "tavily")
            else:
                parsed = _other(ingredient, "other")

        progress = 10 + int((idx + 1) / len(ingredients) * 40)
        await _emit(queue, {
            "type": "ingredient_researched",
            "ingredient": ingredient,
            "progress": progress,
            "safety_rating": parsed.get("safety_rating", "other"),
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
                "safety_rating": qdrant_res.get("safety_rating", "other"),
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
    
    # 3. Apply Rule-Based Classifications
    product_is_veg = True
    product_is_vegan = True
    non_veg_ingredients = []
    processing_levels = []
    
    for res in final_research_results:
        veg_info = classify_veg(res["name"])
        res["is_veg"] = veg_info["is_veg"]
        res["is_vegan"] = veg_info["is_vegan"]
        res["ingredient_source"] = veg_info["source"]
        
        proc_level = classify_processing(res["name"])
        res["processing_level"] = proc_level
        processing_levels.append(proc_level)
        
        if not veg_info["is_veg"]:
            product_is_veg = False
            product_is_vegan = False
            non_veg_ingredients.append({
                "name": res["name"],
                "reason": veg_info["reason"],
                "source": veg_info["source"]
            })
        elif not veg_info["is_vegan"]:
            product_is_vegan = False
            
    overall_processing = get_worst_processing_level(processing_levels)
    if not product_is_veg:
        product_veg_status = "non-veg"
    elif not product_is_vegan:
        product_veg_status = "veg"
    else:
        product_veg_status = "vegan"

    updates = list(state.get("status_updates", []))
    updates.append({
        "type": "research_done",
        "message": "Research complete",
        "count": len(final_research_results),
    })

    await _emit(queue, {"stage": "research", "status": "done", "duration_sec": time.time() - start_time})
    return {
        **state, 
        "research_results": final_research_results, 
        "status_updates": updates,
        "product_veg_status": product_veg_status,
        "non_veg_ingredients": non_veg_ingredients,
        "processing_level": overall_processing
    }

def _other(name: str, source: str) -> Dict[str, Any]:
    return {
        "name": name,
        "aliases": [],
        "safety_rating": "other",
        "health_impact": "No data available.",
        "conditions_affected": [],
        "banned_in": [],
        "daily_limit_mg": None,
        "source": source,
        "confidence": 0.0,
        "is_veg": True,
        "is_vegan": True,
        "ingredient_source": "unknown",
        "processing_level": "unknown"
    }
