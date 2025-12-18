"""Comprehensive test of all 9 directives"""
import asyncio
import aiohttp
import json

CONVERSATION = [
    # Test 1-3: lock_title, lock_logline, add_character
    {
        "msg": "A wedding photographer who stopped believing in love keeps running into an optimistic wedding planner. They clash constantly but keep getting booked for the same weddings.",
        "desc": "Initial pitch",
        "expect": []
    },
    {
        "msg": "Let's call it 'Say I Don't'",
        "desc": "Suggest title",
        "expect": []
    },
    {
        "msg": "Yes, lock it",
        "desc": "Lock title",
        "expect": ["lock_title"]
    },
    {
        "msg": "That logline works",
        "desc": "Approve logline",
        "expect": []
    },
    {
        "msg": "Yes, lock the logline",
        "desc": "Lock logline",
        "expect": ["lock_logline"]
    },
    {
        "msg": "Tell me about the photographer",
        "desc": "Ask about protagonist",
        "expect": ["add_character"]
    },
    {
        "msg": "And the wedding planner?",
        "desc": "Ask about love interest",
        "expect": ["add_character"]
    },

    # Test 4-7: set_theme, set_tone, set_comps, add_to_notebook
    {
        "msg": "The theme should be about learning to trust again after heartbreak. The tone should be witty banter with real emotional depth, like When Harry Met Sally meets The Proposal.",
        "desc": "Set theme, tone, comps",
        "expect": ["set_theme", "set_tone", "set_comps"]
    },
    {
        "msg": "Random creative idea: what if they get trapped in an elevator together during a wedding venue visit?",
        "desc": "Add notebook idea",
        "expect": ["add_to_notebook"]
    },

    # Test 8-9: add_outline_beat, add_scene
    {
        "msg": "For the outline, Act 1 should be: Jaded photographer meets annoyingly optimistic planner at a wedding gone wrong. They clash immediately.",
        "desc": "Add outline beat",
        "expect": ["add_outline_beat"]
    },
    {
        "msg": "For scene 1, title it 'Wedding Disaster' - our photographer is shooting a ceremony when the groom's ex crashes it. Chaos ensues.",
        "desc": "Add scene",
        "expect": ["add_scene"]
    },
]

async def send_message(session, msg, desc, expect_directives):
    """Send message and check for expected directives"""
    url = "http://localhost:8888/chat"

    print(f"\n{'='*80}")
    print(f"👤 USER ({desc}):")
    print(f"{'='*80}")
    print(f"{msg[:100]}{'...' if len(msg) > 100 else ''}\n")

    async with session.post(url, json={"message": msg}) as response:
        if response.status != 200:
            print(f"❌ Error: {await response.text()}")
            return [], ""

        full_response = ""

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
                except json.JSONDecodeError:
                    pass

        print(f"🤖 SYD: {full_response[:100]}{'...' if len(full_response) > 100 else ''}")

        # Extract directives
        import re
        directives = re.findall(r'\[DIRECTIVE:(\w+)\|', full_response)

        if directives:
            print(f"\n📝 DIRECTIVES EMITTED: {', '.join(directives)}")

        # Check expectations
        if expect_directives:
            missing = set(expect_directives) - set(directives)
            unexpected = set(directives) - set(expect_directives)

            if missing:
                print(f"⚠️  MISSING: {', '.join(missing)}")
            if unexpected:
                print(f"ℹ️  BONUS: {', '.join(unexpected)}")
            if not missing:
                print(f"✅ All expected directives emitted")

        return directives, full_response

async def test_all_directives():
    """Test all 9 directives systematically"""
    print("="*80)
    print(" COMPREHENSIVE DIRECTIVE TEST - ALL 9 DIRECTIVES")
    print("="*80)
    print("\nTesting:")
    print("1. lock_title")
    print("2. lock_logline")
    print("3. add_character (protagonist + love interest)")
    print("4. set_theme")
    print("5. set_tone")
    print("6. set_comps")
    print("7. add_to_notebook")
    print("8. add_outline_beat")
    print("9. add_scene")
    print("="*80)

    all_directives_seen = []

    async with aiohttp.ClientSession() as session:
        for turn in CONVERSATION:
            directives, response = await send_message(
                session,
                turn["msg"],
                turn["desc"],
                turn["expect"]
            )
            all_directives_seen.extend(directives)
            await asyncio.sleep(1.5)

        # Check final state
        print(f"\n{'='*80}")
        print(" FINAL STATE VERIFICATION")
        print(f"{'='*80}\n")

        async with session.get("http://localhost:8888/state") as response:
            state = await response.json()

            fields = state.get("fields", {})
            locked = state.get("locked", {})

            # Track which directives were successfully executed
            results = {}

            # 1. lock_title
            results['lock_title'] = locked.get('title', False)
            print(f"1. lock_title: {'✅ PASS' if results['lock_title'] else '❌ FAIL'}")
            if results['lock_title']:
                print(f"   Title: {fields.get('title')}")

            # 2. lock_logline
            results['lock_logline'] = locked.get('logline', False)
            print(f"2. lock_logline: {'✅ PASS' if results['lock_logline'] else '❌ FAIL'}")
            if results['lock_logline']:
                print(f"   Logline: {fields.get('logline', '')[:80]}...")

            # 3. add_character (need at least 2)
            char_count = len(fields.get('characters', []))
            results['add_character'] = char_count >= 2
            print(f"3. add_character: {'✅ PASS' if results['add_character'] else '❌ FAIL'}")
            print(f"   Characters: {char_count}")
            for char in fields.get('characters', []):
                print(f"      - {char.get('name')} ({char.get('role')})")

            # 4. set_theme
            results['set_theme'] = bool(fields.get('theme'))
            print(f"4. set_theme: {'✅ PASS' if results['set_theme'] else '❌ FAIL'}")
            if results['set_theme']:
                print(f"   Theme: {fields.get('theme')}")

            # 5. set_tone
            results['set_tone'] = bool(fields.get('tone'))
            print(f"5. set_tone: {'✅ PASS' if results['set_tone'] else '❌ FAIL'}")
            if results['set_tone']:
                print(f"   Tone: {fields.get('tone')}")

            # 6. set_comps
            results['set_comps'] = bool(fields.get('comps'))
            print(f"6. set_comps: {'✅ PASS' if results['set_comps'] else '❌ FAIL'}")
            if results['set_comps']:
                print(f"   Comps: {fields.get('comps')}")

            # 7. add_to_notebook
            notebook_count = len(fields.get('notebook', []))
            results['add_to_notebook'] = notebook_count >= 1
            print(f"7. add_to_notebook: {'✅ PASS' if results['add_to_notebook'] else '❌ FAIL'}")
            print(f"   Notebook ideas: {notebook_count}")
            for idea in fields.get('notebook', []):
                print(f"      - {idea[:80]}...")

            # 8. add_outline_beat
            outline_count = len(fields.get('outline', []))
            results['add_outline_beat'] = outline_count >= 1
            print(f"8. add_outline_beat: {'✅ PASS' if results['add_outline_beat'] else '❌ FAIL'}")
            print(f"   Outline beats: {outline_count}")
            for beat in fields.get('outline', []):
                print(f"      - {beat[:80]}...")

            # 9. add_scene
            scene_count = len(fields.get('beats', []))
            results['add_scene'] = scene_count >= 1
            print(f"9. add_scene: {'✅ PASS' if results['add_scene'] else '❌ FAIL'}")
            print(f"   Scenes: {scene_count}")
            for scene in fields.get('beats', []):
                print(f"      #{scene.get('number')}: {scene.get('title')}")

            # Summary
            print(f"\n{'='*80}")
            print(" TEST SUMMARY")
            print(f"{'='*80}")

            passed = sum(1 for v in results.values() if v)
            total = len(results)

            print(f"\n📊 RESULTS: {passed}/{total} directives working")
            print(f"\n🔍 DIRECTIVES SEEN: {', '.join(set(all_directives_seen))}")

            if passed == total:
                print(f"\n🎉 ALL DIRECTIVES PASSED!")
            elif passed >= total - 2:
                print(f"\n✅ MOSTLY WORKING - {total - passed} directives need attention")
            else:
                print(f"\n⚠️  NEEDS WORK - {total - passed} directives failing")

            print(f"\n{'='*80}")

            return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(test_all_directives())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
