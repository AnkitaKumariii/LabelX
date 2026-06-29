"""
Supervisor Agent — Hub of the LangGraph workflow.

Routes between Research → Analysis → Critic based on state flags.
"""
from typing import Literal
from agents.state import AnalysisState
import asyncio
import logging

logger = logging.getLogger(__name__)


async def supervisor_node(state: AnalysisState) -> AnalysisState:
    queue = state.get("event_queue")
    retry_count = state.get("retry_count", 0)
    updates = list(state.get("status_updates", []))

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

    if queue:
        await queue.put({
            "type": "supervisor",
            "message": msg,
            "next_agent": next_node,
            "retry_count": retry_count,
        })

    return {**state, "status_updates": updates, "_next_node": next_node}


def route_from_supervisor(state: AnalysisState) -> Literal["research", "analysis", "critic", "__end__"]:
    node = state.get("_next_node", "research")
    if node == "end":
        return "__end__"
    return node
