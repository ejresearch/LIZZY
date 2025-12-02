"""Test bucket queries directly"""
import asyncio
from lizzy.ideate import IdeateSession

async def test_buckets():
    print("Creating session...")
    session = IdeateSession(debug=False)

    print("\nInitializing buckets...")
    for bucket_name in ["scripts", "books", "plays"]:
        rag = session._get_rag_instance(bucket_name)
        if rag:
            print(f"  Initializing {bucket_name}...")
            await rag.initialize_storages()
            session._initialized_buckets.add(bucket_name)
            print(f"  {bucket_name} ready")
        else:
            print(f"  {bucket_name} - no data found")

    print("\nTesting simple queries...")
    test_message = "two roommates fall for same guy"

    queries = session._shape_bucket_queries(test_message)
    print(f"\nGenerated queries:")
    print(f"  Scripts: {queries['scripts']}")
    print(f"  Books: {queries['books']}")
    print(f"  Plays: {queries['plays']}")

    print("\nExecuting queries...")
    insights = await session._get_all_bucket_insights(queries)

    print(f"\nResults:")
    print(f"  Scripts: {len(insights['scripts'])} chars")
    print(f"  Books: {len(insights['books'])} chars")
    print(f"  Plays: {len(insights['plays'])} chars")

if __name__ == "__main__":
    asyncio.run(test_buckets())
