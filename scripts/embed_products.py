import os
import sys
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sqlmodel import Session, select

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from app.utils.db import engine
from app.models import Product

# 1. Setup
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("❌ Error: GOOGLE_API_KEY not found.")
    sys.exit(1)

# NEW SDK INITIALIZATION
client = genai.Client(api_key=API_KEY)

# Initialize Qdrant (Local)
qdrant_path = os.path.join(project_root, "qdrant_data")
qdrant = QdrantClient(path=qdrant_path)
COLLECTION_NAME = "shop_products"

# Reset Collection
if qdrant.collection_exists(COLLECTION_NAME):
    qdrant.delete_collection(COLLECTION_NAME)

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)

def main():
    print(f"--- 🧠 Semantic Indexing (Powered by google-genai SDK) ---")
    
    with Session(engine) as session:
        products = session.exec(select(Product)).all()
        points = []
        
        for product in products:
            text_to_embed = f"Product: {product.name}. Category: {product.category}. Description: {product.description}"
            
            try:
                # --- NEW SDK CALL ---
                response = client.models.embed_content(
                    model="text-embedding-004",
                    contents=text_to_embed
                )
                # The new SDK returns an object, we access .embeddings[0].values
                embedding = response.embeddings[0].values
                
                points.append(PointStruct(
                    id=product.id,
                    vector=embedding,
                    payload={
                        "name": product.name,
                        "price": product.price,
                        "category": product.category,
                        "description": product.description
                    }
                ))
                print(f"   🔹 Embedded: {product.name}")
                
            except Exception as e:
                print(f"   ❌ Failed {product.name}: {e}")

        if points:
            qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
            print(f"✅ Indexed {len(points)} products.")

if __name__ == "__main__":
    main()