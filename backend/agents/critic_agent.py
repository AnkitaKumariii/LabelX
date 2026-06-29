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
    queue = state.get("event_queue")
    report = state.get("report", {})
    user_profile = state.get("user_profile", {})
    ingredients = state.get("ingredients", [])
    retry_count = state.get("retry_count", 0)

    await _emit(queue, {
        "type": "agent_start",
        "agent": "Critic Agent",
        "message": "Running 4-gate validation…",
        "progress": 80,
    })

    failures: List[str] = []
    gates_results: Dict[str, bool] = {}

    # ── Gate 1: Completeness ──────────────────────────────────────────────────
    report_ingredient_names = [
        i.get("name", "").lower()
        for i in report.get("ingredients", [])
    ]
    missing = [
        ing for ing in ingredients
        if ing.lower() not in report_ingredient_names
    ]
    if missing:
        failures.append(
            f"GATE 1 FAIL (Completeness): Missing ingredients in report: {', '.join(missing[:5])}"
        )
        gates_results["completeness"] = False
    else:
        gates_results["completeness"] = True

    # ── Gate 2: Allergen Check ────────────────────────────────────────────────
    allergies = [a.lower() for a in user_profile.get("allergies", [])]
    allergen_alerts = [
        a.lower() for a in report.get("summary", {}).get("allergen_alerts", [])
    ]
    # Check if any ingredient name contains an allergen keyword and it's flagged
    unflagged_allergens = []
    for allergen in allergies:
        ingredient_match = any(allergen in ing.lower() for ing in ingredients)
        if ingredient_match:
            flagged = any(allergen in alert for alert in allergen_alerts)
            if not flagged:
                unflagged_allergens.append(allergen)
    if unflagged_allergens:
        failures.append(
            f"GATE 2 FAIL (Allergen Check): These user allergens not flagged: {', '.join(unflagged_allergens)}"
        )
        gates_results["allergen_check"] = False
    else:
        gates_results["allergen_check"] = True

    # ── Gate 3: Score Consistency ──────────────────────────────────────────────
    harmful_count = report.get("summary", {}).get("harmful_count", 0)
    health_score = report.get("summary", {}).get("health_score", 100)
    if harmful_count >= 3 and health_score >= 40:
        failures.append(
            f"GATE 3 FAIL (Score Consistency): {harmful_count} harmful ingredients "
            f"but health_score={health_score} (must be < 40)"
        )
        gates_results["score_consistency"] = False
    else:
        gates_results["score_consistency"] = True

    # ── Gate 4: Personalization ────────────────────────────────────────────────
    conditions = user_profile.get("health_conditions", [])
    personalized_summary = report.get("summary", {}).get("personalized_summary", "")
    personalized_notes = [
        i.get("personalized_note") or ""
        for i in report.get("ingredients", [])
    ]
    has_condition_mention = any(
        cond.lower() in personalized_summary.lower() or
        any(cond.lower() in note.lower() for note in personalized_notes)
        for cond in conditions
    )
    if conditions and not has_condition_mention:
        failures.append(
            f"GATE 4 FAIL (Personalization): Report doesn't address user conditions: {', '.join(conditions)}"
        )
        gates_results["personalization"] = False
    else:
        gates_results["personalization"] = True

    passed = len(failures) == 0

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
        logger.info("[Critic] All 4 gates passed ✓")
        updates.append({"type": "critic_passed", "message": "All validation gates passed"})
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
    return {
        **state,
        "report": None,
        "validated": False,
        "retry_count": new_retry,
        "feedback": feedback_msg,
        "status_updates": updates,
    }
