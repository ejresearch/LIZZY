"""Test multi-turn conversation to verify directive tracking"""
import asyncio
import aiohttp
import json

# Simulate a full conversation flow with confirmations
CONVERSATION_TURNS = [
    {
        "message": """Maude and Ivy are in their early 20s living in DC. Maude is from a well off family - mom did PR for a smattering of public figures so her 'entry level job' allows her a lifestyle that transcends her paycheck. Ivy is in her second year of grad school and outside of that, she's pretty nonchalant about everything - Maude decorated their whole apartment leaving out Ivy's one piece of decor and she couldn't care less. Despite their differences, they've had a solid friendship and chill living situation, almost like sisters. Ivy rarely joins Maude for a night out, but this quarter she's finished finals early and gotten great scores so she joins her and meets Lars who she instantly hits it off with. They chat for an hour, exchange numbers, and then she doesn't see him the rest of the night. The next morning, Ivy and Maude are unloading groceries or making breakfast and they chat about their night where they slowly realize they both met and felt like they clicked with Lars. At that point they'd either both texted him and he'd only responded to Ivy or like only texted Ivy. This makes Maude noticeably jealous and while Ivy would usually give in, for once, she thinks this is someone/something she really wants.""",
        "description": "Initial story pitch"
    },
    {
        "message": "Yes, I love 'Room for One' as the title. Let's lock that in.",
        "description": "Title confirmation (should trigger lock_title directive)"
    },
    {
        "message": "Perfect. That logline captures it exactly. Lock it.",
        "description": "Logline confirmation (should trigger lock_logline directive)"
    },
    {
        "message": "The theme is 'choosing yourself for the first time' - that's exactly what I want to explore.",
        "description": "Theme confirmation (should trigger set_theme directive)"
    }
]

async def send_message(session, message, turn_number, description):
    """Send a message and collect the full response"""
    url = "http://localhost:8888/chat"

    print(f"\n{'='*80}")
    print(f"TURN {turn_number}: {description}")
    print(f"{'='*80}")
    print(f"SENDING: {message[:100]}{'...' if len(message) > 100 else ''}")
    print(f"\nRESPONSE:")
    print("-" * 80)

    try:
        async with session.post(url, json={"message": message}) as response:
            if response.status != 200:
                print(f"❌ ERROR: {response.status} - {await response.text()}")
                return None

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
                            print(chunk, end='', flush=True)
                    except json.JSONDecodeError:
                        pass

            print("\n" + "-" * 80)
            print(f"✅ Turn {turn_number} complete: {len(full_response)} chars")
            return full_response

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

async def check_state(session):
    """Check the current state after conversation"""
    url = "http://localhost:8888/state"

    try:
        async with session.get(url) as response:
            if response.status == 200:
                state = await response.json()
                return state
            else:
                print(f"❌ State check failed: {response.status}")
                return None
    except Exception as e:
        print(f"❌ State check error: {e}")
        return None

async def test_multi_turn():
    """Run multi-turn conversation and verify directive tracking"""
    print("="*80)
    print("MULTI-TURN DIRECTIVE TRACKING TEST")
    print("="*80)
    print(f"Testing {len(CONVERSATION_TURNS)} conversation turns...")

    async with aiohttp.ClientSession() as session:
        # Run conversation turns
        for i, turn in enumerate(CONVERSATION_TURNS, 1):
            response = await send_message(
                session,
                turn["message"],
                i,
                turn["description"]
            )

            if response is None:
                print(f"❌ Test failed at turn {i}")
                return

            # Brief pause between turns (simulate human timing)
            await asyncio.sleep(1)

        # Check final state
        print(f"\n{'='*80}")
        print("CHECKING FINAL STATE")
        print(f"{'='*80}")

        state = await check_state(session)

        if state:
            print("\n📊 STATE SUMMARY:")
            print("-" * 80)

            # Check fields
            fields = state.get("fields", {})
            locked = state.get("locked", {})

            print(f"\n🔒 LOCKED FIELDS:")
            print(f"   Title: {fields.get('title')} {'✅' if locked.get('title') else '❌'}")
            print(f"   Logline: {fields.get('logline')[:80] if fields.get('logline') else 'None'}{'...' if fields.get('logline') and len(fields.get('logline')) > 80 else ''} {'✅' if locked.get('logline') else '❌'}")

            print(f"\n📝 STORY DATA:")
            print(f"   Theme: {fields.get('theme') or 'Not set'}")
            print(f"   Tone: {fields.get('tone') or 'Not set'}")
            print(f"   Comps: {fields.get('comps') or 'Not set'}")

            print(f"\n👥 CHARACTERS: {len(fields.get('characters', []))} tracked")
            for char in fields.get('characters', []):
                print(f"   - {char.get('name')} ({char.get('role')})")

            print(f"\n🎬 SCENES: {len(fields.get('beats', []))} tracked")
            for beat in fields.get('beats', [])[:5]:  # Show first 5
                print(f"   {beat.get('number')}. {beat.get('title')}")
            if len(fields.get('beats', [])) > 5:
                print(f"   ... and {len(fields.get('beats', [])) - 5} more")

            print(f"\n📓 NOTEBOOK: {len(fields.get('notebook', []))} ideas saved")

            print(f"\n🎯 STAGE: {state.get('stage', 'unknown')}")

            # Verify expected directives worked
            print(f"\n{'='*80}")
            print("VERIFICATION RESULTS:")
            print(f"{'='*80}")

            success = True

            if not locked.get('title'):
                print("❌ FAIL: Title should be locked after turn 2")
                success = False
            else:
                print("✅ PASS: Title locked")

            if not locked.get('logline'):
                print("❌ FAIL: Logline should be locked after turn 3")
                success = False
            else:
                print("✅ PASS: Logline locked")

            if not fields.get('theme'):
                print("❌ FAIL: Theme should be set after turn 4")
                success = False
            else:
                print("✅ PASS: Theme set")

            if len(fields.get('characters', [])) < 2:
                print(f"⚠️  WARN: Expected at least 2 characters (got {len(fields.get('characters', []))})")
            else:
                print(f"✅ PASS: Characters tracked ({len(fields.get('characters', []))})")

            if success:
                print(f"\n{'='*80}")
                print("✅ ALL TESTS PASSED - Directive tracking working!")
                print(f"{'='*80}")
            else:
                print(f"\n{'='*80}")
                print("❌ SOME TESTS FAILED - Check directive execution")
                print(f"{'='*80}")
        else:
            print("❌ Could not retrieve final state")

if __name__ == "__main__":
    try:
        asyncio.run(test_multi_turn())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
