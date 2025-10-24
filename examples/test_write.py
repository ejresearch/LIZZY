#!/usr/bin/env python3
"""
Quick test of the WRITE module.

Tests:
1. Loading scene context
2. Generating a draft (without blueprint)
3. Saving to database
4. Retrieving drafts
"""

import asyncio
from lizzy.write import WriteModule

async def main():
    print("\n" + "="*60)
    print("Testing WRITE Module")
    print("="*60 + "\n")

    writer = WriteModule('the_proposal_2_0')

    # Test 1: Load scene context
    print("1. Loading scene 1 context...")
    context = writer.load_scene_context(1)

    if not context:
        print("❌ Scene not found!")
        return

    print(f"✅ Loaded: Scene {context.scene_number}: {context.title}")
    print(f"   Description: {context.description}")
    print(f"   Has blueprint: {context.blueprint is not None}")

    # Test 2: Generate draft
    print("\n2. Generating draft...")
    print("   (This may take 20-30 seconds...)\n")

    try:
        draft = await writer.generate_draft(
            context,
            model="gpt-4o",
            target_words=800
        )

        print(f"✅ Generated draft:")
        print(f"   Version: {draft.version}")
        print(f"   Word count: {draft.word_count}")
        print(f"   Tokens: {draft.tokens_used}")
        print(f"   Cost: ${draft.cost_estimate:.4f}")

        # Show first 200 characters
        print(f"\n   Preview: {draft.content[:200]}...")

    except Exception as e:
        print(f"❌ Error generating draft: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 3: Save draft
    print("\n3. Saving draft to database...")

    try:
        draft_id = writer.save_draft(draft)
        print(f"✅ Saved as draft ID: {draft_id}")
    except Exception as e:
        print(f"❌ Error saving: {e}")
        return

    # Test 4: Retrieve drafts
    print("\n4. Retrieving all drafts for scene 1...")

    try:
        all_drafts = writer.get_all_drafts(1)
        print(f"✅ Found {len(all_drafts)} draft(s):")

        for d in all_drafts:
            print(f"   v{d.version}: {d.word_count} words, {d.created_at}")
    except Exception as e:
        print(f"❌ Error retrieving: {e}")
        return

    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
