"""Test that existing RAG buckets work with new LightRAG version."""

import asyncio
import os
from pathlib import Path

# Load API key from parent .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

async def test_buckets():
    from lightrag import LightRAG, QueryParam
    from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete

    buckets_dir = Path(__file__).parent.parent / "rag_buckets"

    for bucket_name in ["books", "plays", "scripts"]:
        bucket_path = buckets_dir / bucket_name
        print(f"\n{'='*50}")
        print(f"Testing: {bucket_name}")
        print(f"{'='*50}")

        try:
            rag = LightRAG(
                working_dir=str(bucket_path),
                llm_model_func=gpt_4o_mini_complete,
                embedding_func=openai_embed,
            )
            await rag.initialize_storages()

            # Quick test query
            test_query = "romantic comedy structure" if bucket_name == "books" else \
                         "love and conflict" if bucket_name == "plays" else \
                         "meet cute scene"

            result = await rag.aquery(test_query, param=QueryParam(mode="hybrid"))

            print(f"✓ Loaded successfully")
            print(f"✓ Query returned {len(result)} chars")
            print(f"  Preview: {result[:300]}...")

        except Exception as e:
            print(f"✗ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_buckets())
