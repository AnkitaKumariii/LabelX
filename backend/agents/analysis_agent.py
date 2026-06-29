"""
Analysis Agent — Generates personalized food safety report via Gemini 2.0 Flash.

Adapts language (beginner vs expert) and personalizes warnings for user conditions.
Accepts optional feedback from Critic for retry runs.
"""
import logging
from agents.state import AnalysisState

logger = logging.getLogger(__name__)


async def _emit(queue, event: dict) -> None:
    if queue:
        await queue.put(event)


async def analysis_node(state: AnalysisState) -> AnalysisState:
    from services.gemini_service import generate_analysis_report

    queue = state.get("event_queue")
    retry_count = state.get("retry_count", 0)
    feedback = state.get("feedback")

    msg = (
        f"Generating report (retry #{retry_count})…"
        if retry_count > 0
        else "Generating personalized safety report…"
    )
    await _emit(queue, {
        "type": "agent_start",
        "agent": "Analysis Agent",
        "message": msg,
        "progress": 55,
    })

    try:
        report = await generate_analysis_report(
            ingredients=state.get("ingredients", []),
            research_results=state.get("research_results", []),
            user_profile=state.get("user_profile", {}),
            feedback=feedback,
            retry_count=retry_count,
        )

        score = report.get("summary", {}).get("health_score", 50)

        await _emit(queue, {
            "type": "analysis_done",
            "message": "Report generated — sending to Critic for validation…",
            "progress": 75,
            "score": score,
        })

        updates = list(state.get("status_updates", []))
        updates.append({"type": "analysis_done", "score": score})

        return {
            **state,
            "report": report,
            "score": score,
            "status_updates": updates,
            # Clear feedback after consuming it
            "feedback": None,
        }

    except Exception as e:
        logger.error(f"[Analysis] Gemini error: {e}")
        await _emit(queue, {
            "type": "error",
            "agent": "Analysis Agent",
            "message": str(e),
        })
        return {**state, "error": str(e)}
