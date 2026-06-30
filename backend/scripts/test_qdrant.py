import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.qdrant_service import search_ingredients_batch, search_ingredient

async def main():
    print("Testing Qdrant search...")
    ingredients = ["Aspartame", "Water", "Sugar", "Sodium Bicarbonate", "NonExistentThing"]
    
    # Test batch
    print("Running batch search:")
    results = await search_ingredients_batch(ingredients)
    for ing, res in zip(ingredients, results):
        if res:
            print(f"{ing}: Found -> {res['name']} (score: {res.get('confidence')})")
        else:
            print(f"{ing}: No result")

if __name__ == "__main__":
    asyncio.run(main())
