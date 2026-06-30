import asyncio
import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph import graph

async def main():
    print("Testing complete workflow with simulated Critic rejection...")
    
    initial_state = {
        "ingredients": ["Water", "High Fructose Corn Syrup", "Red 40"],
        "user_profile": {
            "health_conditions": ["diabetes"],
            "allergies": [],
            "expertise_level": "beginner"
        },
        "research_results": [],
        "report": None,
        "score": None,
        "feedback": None,
        "retry_count": 0,
        "status_updates": [],
        "validated": False,
        "error": None,
        "event_queue": None,
    }
    
    # We will patch validate_report_with_critic to fail on the FIRST try, and succeed on the SECOND.
    call_count = {"count": 0}
    original_validate = None
    
    # Need to import here to get the real one before patching
    import services.gemini_service
    original_validate = services.gemini_service.validate_report_with_critic
    
    async def fake_validate(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            print("  -> [Mock] Critic rejecting first attempt.")
            return False, {}, ["Simulated Failure: Missing personalization for diabetes"]
        print("  -> [Mock] Critic passing second attempt.")
        # Pass through to the real one or just return true
        return True, {"completeness": True, "personalization": True}, []

    with patch('services.gemini_service.validate_report_with_critic', side_effect=fake_validate):
        final_state = await graph.ainvoke(initial_state)
    
    if final_state.get("invalid_product"):
        print("FAILED: Flagged as invalid product.")
    elif final_state.get("retry_count", 0) > 0:
        print(f"SUCCESS: Workflow completed with {final_state.get('retry_count')} retries.")
        print(f"Final Score: {final_state.get('score')}")
    else:
        print("FAILED: Did not trigger retry loop.")

if __name__ == "__main__":
    asyncio.run(main())
