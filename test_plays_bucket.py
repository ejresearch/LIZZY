"""Test plays bucket specifically"""
import asyncio
from pathlib import Path
from lightrag import LightRAG, QueryParam

async def test_plays():
    bucket_path = Path("./rag_buckets/plays")
    print(f"Testing plays bucket at: {bucket_path}")
    print(f"Bucket exists: {bucket_path.exists()}")

    rag = LightRAG(
        working_dir=str(bucket_path),
        llm_model_func=None  # Don't need LLM for query
    )

    print("\nInitializing...")
    await rag.initialize_storages()
    print("Initialized")

    # Test simple queries
    queries = [
        "romantic comedy",
        "relationship",
        "love",
        "roommates"
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        try:
            result = await asyncio.wait_for(
                rag.aquery(query, param=QueryParam(mode="local")),
                timeout=30.0
            )
            print(f"  Result: {len(result or '')} chars")
            if result:
                print(f"  Preview: {result[:200]}...")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_plays())
