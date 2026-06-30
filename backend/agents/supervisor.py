"""
Supervisor Agent — Hub of the LangGraph workflow.

Routes between Research → Analysis → Critic based on state flags.
"""
import time
from typing import Literal
from agents.state import AnalysisState
import asyncio
import logging

logger = logging.getLogger(__name__)


async def _emit(queue, event: dict) -> None:
    if queue:
        await queue.put(event)


async def supervisor_node(state: AnalysisState) -> AnalysisState:
    from services.gemini_service import check_relevance

    start_time = time.time()
    queue = state.get("event_queue")
    retry_count = state.get("retry_count", 0)
    updates = list(state.get("status_updates", []))
    ingredients = state.get("ingredients", [])

    await _emit(queue, {"stage": "supervisor", "status": "running"})

    # 1. Relevance Gate Check (if not already checked)
    if not state.get("research_results") and not state.get("invalid_product", False):
        ingredients_text = ", ".join(ingredients)
        is_food, reason = await check_relevance(ingredients_text)
        if not is_food:
            msg = f"Invalid product detected: {reason}"
            logger.warning(f"[Supervisor] {msg}")
            updates.append({"type": "supervisor", "message": msg, "next": "end"})
            await _emit(queue, {
                "type": "error",
                "message": msg
            })
            await _emit(queue, {"stage": "supervisor", "status": "done", "duration_sec": time.time() - start_time})
            return {**state, "invalid_product": True, "invalid_reason": reason, "status_updates": updates, "_next_node": "end"}

    # 2. Normal Routing Logic
    if not state.get("research_results"):
        msg = "Routing to Research Agent…"
        next_node = "research"
    elif not state.get("report"):
        if retry_count >= 3:
            msg = "Max retries reached — finalizing best-effort report"
            next_node = "end"
        else:
            if retry_count > 0:
                msg = f"Retry #{retry_count}: routing back to Analysis Agent with feedback"
            else:
                msg = "Routing to Analysis Agent…"
            next_node = "analysis"
    elif not state.get("validated"):
        msg = "Routing to Critic Agent for validation…"
        next_node = "critic"
    else:
        msg = "Analysis validated — complete!"
        next_node = "end"

    updates.append({"type": "supervisor", "message": msg, "next": next_node})
    logger.info(f"[Supervisor] {msg}")

    await _emit(queue, {
        "type": "supervisor",
        "message": msg,
        "next_agent": next_node,
        "retry_count": retry_count,
    })

    await _emit(queue, {"stage": "supervisor", "status": "done", "duration_sec": time.time() - start_time})
    return {**state, "status_updates": updates, "_next_node": next_node}


def route_from_supervisor(state: AnalysisState) -> Literal["research", "analysis", "critic", "__end__"]:
    node = state.get("_next_node", "research")
    if node == "end":
        return "__end__"
    return node
