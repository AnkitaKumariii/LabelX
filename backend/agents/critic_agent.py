"""
Critic Agent — Validates the analysis report through 4 quality gates.

Gates:
  1. Completeness   — All ingredients have a report entry
  2. Allergen Check — All user allergens are flagged if present
  3. Score Consistency — 3+ harmful must score < 40
  4. Personalization — User conditions must influence the report

On failure: clears report, sends specific feedback, increments retry_count.
After 3 failures: keeps best-effort report, adds disclaimer, forces validated=True.
"""
import logging
from typing import List, Dict, Any, Tuple
from agents.state import AnalysisState

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def _emit(queue, event: dict) -> None:
    if queue:
        await queue.put(event)


async def critic_node(state: AnalysisState) -> AnalysisState:
    import time
    from services.gemini_service import validate_report_with_critic

    start_time = time.time()
    queue = state.get("event_queue")
    report = state.get("report", {})
    user_profile = state.get("user_profile", {})
    ingredients = state.get("ingredients", [])
    retry_count = state.get("retry_count", 0)

    await _emit(queue, {"stage": "critic", "status": "running"})
    await _emit(queue, {
        "type": "agent_start",
        "agent": "Critic Agent",
        "message": "Running 6-gate validation via LLM…",
        "progress": 80,
    })

    passed, gates_results, failures = await validate_report_with_critic(ingredients, report, user_profile)

    await _emit(queue, {
        "type": "critic_result",
        "passed": passed,
        "gates": gates_results,
        "failures": failures,
        "retry_count": retry_count,
        "progress": 90,
    })

    updates = list(state.get("status_updates", []))

    if passed:
        logger.info("[Critic] All 6 gates passed ✓")
        updates.append({"type": "critic_passed", "message": "All validation gates passed"})
        await _emit(queue, {"stage": "critic", "status": "done", "duration_sec": time.time() - start_time})
        return {**state, "validated": True, "status_updates": updates}

    # Failed — decide whether to retry or accept best-effort
    new_retry = retry_count + 1
    feedback_msg = "Validation failed. Please fix:\n" + "\n".join(failures)
    logger.warning(f"[Critic] Gates failed (attempt {new_retry}): {failures}")

    if new_retry >= MAX_RETRIES:
        # Add disclaimer and force-validate
        logger.warning("[Critic] Max retries reached — returning best-effort with disclaimer")
        report_copy = dict(report)
        report_copy["disclaimer"] = (
            "⚠️ This report may be incomplete. Some validation checks did not pass "
            "after multiple attempts. Please consult a healthcare professional."
        )
        summary = dict(report_copy.get("summary", {}))
        summary["has_disclaimer"] = True
        report_copy["summary"] = summary

        updates.append({"type": "critic_disclaimer", "message": "Best-effort report with disclaimer"})
        await _emit(queue, {"stage": "critic", "status": "done", "duration_sec": time.time() - start_time})
        return {
            **state,
            "report": report_copy,
            "validated": True,
            "retry_count": new_retry,
            "feedback": feedback_msg,
            "status_updates": updates,
        }

    # Clear report to trigger re-analysis
    updates.append({"type": "critic_rejected", "failures": failures, "retry": new_retry})
    await _emit(queue, {"stage": "critic", "status": "done", "duration_sec": time.time() - start_time})
    return {
        **state,
        "report": None,
        "validated": False,
        "retry_count": new_retry,
        "feedback": feedback_msg,
        "status_updates": updates,
    }
