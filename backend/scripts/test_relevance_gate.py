import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph import graph

async def main():
    print("Testing relevance gate with invalid input...")
    
    initial_state = {
        "ingredients": ["Water", "Sodium Laureth Sulfate", "Fragrance", "Cocamidopropyl Betaine"],
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
        print("SUCCESS: Relevance gate successfully blocked the invalid product.")
        print(f"Reason given: {final_state.get('invalid_reason')}")
    else:
        print("FAILED: Did not catch the invalid product (shampoo ingredients)!")

if __name__ == "__main__":
    asyncio.run(main())
