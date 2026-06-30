import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph import graph

async def main():
    print("Testing simple valid ingredient list workflow...")
    
    initial_state = {
        "ingredients": ["Water", "Sugar", "Ascorbic Acid"],
        "user_profile": {
            "health_conditions": [],
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
    
    final_state = await graph.ainvoke(initial_state)
    
    if final_state.get("invalid_product"):
        print(f"FAILED: Falsely flagged as invalid product: {final_state.get('invalid_reason')}")
    else:
        print("SUCCESS: Valid workflow completed.")
        print(f"Final Score: {final_state.get('score')}")
        print("Status updates:")
        for update in final_state.get("status_updates", []):
            print(" -", update)

if __name__ == "__main__":
    asyncio.run(main())
