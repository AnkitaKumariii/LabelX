import asyncio
import os
import sys

# Setup paths and environment
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv()

from graph import graph

async def main():
    print("Testing Rule-Based Veg/Non-Veg & Processing Classification...\n")

    # Mock user profile: Vegetarian
    user_profile = {
        "profile_id": "test-veg",
        "name": "Test User",
        "health_conditions": [],
        "allergies": [],
        "dietary_preference": "vegetarian",
        "expertise_level": "beginner"
    }

    # Test ingredients: Gelatin (non-veg), Carmine (non-veg), Maltodextrin (processed), Water (raw)
    ingredients = ["Gelatin", "Carmine", "Maltodextrin", "Water"]

    initial_state = {
        "ingredients": ingredients,
        "user_profile": user_profile,
        "research_results": [],
        "report": None,
        "score": None,
        "feedback": None,
        "retry_count": 0,
        "status_updates": [],
        "validated": False,
        "error": None,
        "event_queue": asyncio.Queue() # Need a queue to prevent graph errors, even though we won't read it
    }

    print("Running Graph Workflow...")
    
    # Run the graph
    try:
        final_state = await graph.ainvoke(initial_state)
        
        print("\n--- RESULTS ---")
        
        # 1. Assert the rule-based classification in Research Agent worked
        print(f"Product Veg Status: {final_state.get('product_veg_status')}")
        print(f"Processing Level: {final_state.get('processing_level')}")
        
        non_veg = final_state.get('non_veg_ingredients', [])
        print(f"Non-Veg Ingredients found: {len(non_veg)}")
        for i in non_veg:
            print(f" - {i['name']} (Reason: {i['reason']}, Source: {i['source']})")
            
        assert final_state.get('product_veg_status') == 'non-veg', "Failed to flag product as non-veg"
        assert final_state.get('processing_level') == 'processed', "Failed to flag worst processing level"
        assert len(non_veg) == 2, "Failed to identify all non-veg ingredients"
        
        # 2. Check the report output
        report = final_state.get('report')
        if report:
            summary = report.get('summary', {})
            warnings = summary.get('top_warnings', [])
            pers_summary = summary.get('personalized_summary', '')
            
            print("\nReport Summary:")
            print(f"Top Warnings: {warnings}")
            print(f"Personalized Summary: {pers_summary}")
            
            # Check if critical warning is present
            critical_warning_found = any('CRITICAL WARNING' in w or 'non-compliant' in w.lower() or 'vegetarian' in w.lower() for w in warnings) or \
                                     'vegetarian' in pers_summary.lower()
            
            print(f"Critical Warning found: {critical_warning_found}")
            
        print("\nTest completed successfully!")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
