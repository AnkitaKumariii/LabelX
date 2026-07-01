import os
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from dotenv import load_dotenv

# Get the directory of the current script to reliably find .env
script_dir = Path(__file__).parent.resolve()
env_path = script_dir.parent / '.env' # Resolves to backend/.env

# Load env variables
load_dotenv(env_path)

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

collection_name = os.getenv("QDRANT_COLLECTION_NAME", "food_additives")

# Get collection info
info = client.get_collection(collection_name=collection_name)
print(f"Collection status: {info.status}")
print(f"Total points: {info.points_count}")

# Fetch the first 5 records (with their payload)
records = client.scroll(
    collection_name=collection_name,
    limit=5,
    with_payload=True,
    with_vectors=False
)

print("\n--- Sample Data ---")
for record in records[0]:
    print(record.payload)
