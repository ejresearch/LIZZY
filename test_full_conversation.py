"""Full end-to-end test of directive system with complete Syd conversation"""
import asyncio
import aiohttp
import json

CONVERSATION = [
    {
        "msg": "I have an idea for a romcom. A burned-out wedding planner who's given up on love gets assigned to plan her ex-fiancé's wedding. She has to work with his new bride's overly enthusiastic best man who believes in soulmates and grand gestures.",
        "desc": "Initial pitch"
    },
    {
        "msg": "I like 'The Last Wedding' as the title",
        "desc": "User suggests title"
    },
    {
        "msg": "Yes, lock it",
        "desc": "User confirms title lock"
    },
    {
        "msg": "That logline is perfect",
        "desc": "User approves logline"
    },
    {
        "msg": "Yes, lock the logline",
        "desc": "User confirms logline lock"
    },
    {
        "msg": "Tell me more about the wedding planner - what's her backstory?",
        "desc": "User asks about protagonist"
    },
    {
        "msg": "And what about the best man?",
        "desc": "User asks about love interest"
    }
]

async def send_message(session, msg, desc):
    """Send message and return full response"""
    url = "http://localhost:8888/chat"

    print(f"\n{'='*80}")
    print(f"👤 USER ({desc}):")
    print(f"{'='*80}")
    print(f"{msg}\n")

    async with session.post(url, json={"message": msg}) as response:
        if response.status != 200:
            print(f"❌ Error: {await response.text()}")
            return ""

        full_response = ""
        print(f"🤖 SYD:")
        print(f"{'-'*80}")

        async for line in response.content:
            line_text = line.decode('utf-8').strip()

            if line_text.startswith('data: '):
                data_str = line_text[6:]
                if data_str == '[DONE]':
                    break

                try:
                    data = json.loads(data_str)
                    if data.get('type') == 'chunk':
                        chunk = data.get('content', '')
                        full_response += chunk
                        print(chunk, end='', flush=True)
                except json.JSONDecodeError:
                    pass

        print(f"\n{'-'*80}")

        # Check for directives
        if "[DIRECTIVE:" in full_response:
            print("\n📝 DIRECTIVES DETECTED (will be stripped from user view):")
            import re
            directives = re.findall(r'\[DIRECTIVE:([^\]]+)\]', full_response)
            for d in directives:
                print(f"   - {d}")

        # Check for asking pattern
        if "should i lock" in full_response.lower() or "lock this" in full_response.lower():
            print("\n🔔 SYD IS ASKING FOR PERMISSION TO LOCK")

        return full_response

async def test_full_conversation():
    """Run complete conversation showing all phases"""
    print("="*80)
    print(" FULL DIRECTIVE SYSTEM TEST - COMPLETE SYD CONVERSATION")
    print("="*80)
    print("\nThis test demonstrates:")
    print("- Permission-asking pattern (AI asks before locking)")
    print("- Extended character tracking (age, personality, flaw, etc.)")
    print("- Outline and notebook tracking")
    print("- Complete database persistence")
    print("="*80)

    async with aiohttp.ClientSession() as session:
        for turn in CONVERSATION:
            await send_message(session, turn["msg"], turn["desc"])
            await asyncio.sleep(1.5)

        # Check final state
        print(f"\n{'='*80}")
        print(" FINAL SESSION STATE")
        print(f"{'='*80}\n")

        async with session.get("http://localhost:8888/state") as response:
            state = await response.json()

            fields = state.get("fields", {})
            locked = state.get("locked", {})

            print(f"📋 PHASE 1 - LOCKED FIELDS:")
            print(f"   Title: {fields.get('title')} {'✅ LOCKED' if locked.get('title') else '❌ NOT LOCKED'}")
            print(f"   Logline: {fields.get('logline', '')[:80]}...")
            print(f"            {'✅ LOCKED' if locked.get('logline') else '❌ NOT LOCKED'}")

            print(f"\n👥 PHASE 2 - CHARACTERS ({len(fields.get('characters', []))} tracked):")
            for char in fields.get('characters', []):
                print(f"\n   {char.get('name')} ({char.get('role')}):")
                if char.get('age'):
                    print(f"      Age: {char.get('age')}")
                if char.get('personality'):
                    print(f"      Personality: {char.get('personality')}")
                if char.get('flaw'):
                    print(f"      Flaw: {char.get('flaw')}")
                if char.get('description'):
                    print(f"      Description: {char.get('description')}")
                if char.get('backstory'):
                    print(f"      Backstory: {char.get('backstory')}")

            print(f"\n📖 OUTLINE BEATS ({len(fields.get('outline', []))}):")
            for i, beat in enumerate(fields.get('outline', []), 1):
                print(f"   {i}. {beat}")

            print(f"\n📓 NOTEBOOK IDEAS ({len(fields.get('notebook', []))}):")
            for idea in fields.get('notebook', []):
                print(f"   - {idea}")

            print(f"\n🎬 OTHER METADATA:")
            print(f"   Theme: {fields.get('theme') or 'Not set'}")
            print(f"   Tone: {fields.get('tone') or 'Not set'}")
            print(f"   Comps: {fields.get('comps') or 'Not set'}")

            print(f"\n{'='*80}")
            print(" TEST SUMMARY")
            print(f"{'='*80}")

            success_count = 0
            total_checks = 0

            # Check title locked
            total_checks += 1
            if locked.get('title'):
                print("✅ Title locked successfully")
                success_count += 1
            else:
                print("❌ Title not locked")

            # Check logline locked
            total_checks += 1
            if locked.get('logline'):
                print("✅ Logline locked successfully")
                success_count += 1
            else:
                print("❌ Logline not locked")

            # Check characters tracked
            total_checks += 1
            if len(fields.get('characters', [])) >= 2:
                print(f"✅ Characters tracked ({len(fields.get('characters', []))} characters)")
                success_count += 1
            else:
                print(f"❌ Insufficient characters tracked ({len(fields.get('characters', []))})")

            # Check for extended character fields
            total_checks += 1
            has_extended = any(
                char.get('age') or char.get('personality') or char.get('flaw')
                for char in fields.get('characters', [])
            )
            if has_extended:
                print("✅ Extended character fields captured (age/personality/flaw)")
                success_count += 1
            else:
                print("⚠️  No extended character fields captured")

            print(f"\n{'='*80}")
            print(f" RESULT: {success_count}/{total_checks} checks passed")
            print(f"{'='*80}")

            if success_count == total_checks:
                print("\n🎉 ALL TESTS PASSED! Directive system fully operational.")
            elif success_count >= total_checks - 1:
                print("\n✅ MOSTLY WORKING - Minor issues detected")
            else:
                print("\n⚠️  NEEDS ATTENTION - Multiple checks failed")

if __name__ == "__main__":
    try:
        asyncio.run(test_full_conversation())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
