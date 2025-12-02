"""Test manual command directives"""
import asyncio
import aiohttp
import json

CONVERSATION = [
    {
        "msg": "A jaded travel writer who's lost her sense of wonder meets an amateur astronomer who still believes in magic. They're both attending a remote star-gazing festival in the desert.",
        "desc": "Initial pitch"
    },
    {
        "msg": "Let's call it 'Written in the Stars'",
        "desc": "Suggest title"
    },
    {
        "msg": "Yes, lock it",
        "desc": "Lock title"
    },
    {
        "msg": "Perfect logline",
        "desc": "Approve logline"
    },
    {
        "msg": "Yes",
        "desc": "Lock logline"
    },
    {
        "msg": "She's Luna Chen, early 30s travel writer. Used to be full of wanderlust but now everything feels the same. She's cynical, guarded, afraid to be vulnerable again after her last relationship.",
        "desc": "Discuss protagonist"
    },
    {
        "msg": "/character Luna",
        "desc": "MANUAL COMMAND: Track Luna as character"
    },
    {
        "msg": "He's Oliver, mid-30s high school science teacher and amateur astronomer. Earnest, optimistic, sees beauty everywhere. His flaw is he's maybe too trusting.",
        "desc": "Discuss love interest"
    },
    {
        "msg": "/character Oliver",
        "desc": "MANUAL COMMAND: Track Oliver as character"
    },
    {
        "msg": "/beat Act 1: Luna arrives at desert festival, encounters Oliver during meteor shower",
        "desc": "MANUAL COMMAND: Add outline beat"
    },
    {
        "msg": "/scene 1 Desert Arrival",
        "desc": "MANUAL COMMAND: Add first scene"
    }
]

async def send_message(session, msg, desc):
    """Send message and return response"""
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

        # Extract and display directives
        import re
        directives = re.findall(r'\[DIRECTIVE:(\w+)\|([^\]]+)\]', full_response)
        if directives:
            print("\n📝 DIRECTIVES EMITTED:")
            for action, params in directives:
                print(f"   - {action}: {params}")

        return full_response

async def test_manual_commands():
    """Test manual command system"""
    print("="*80)
    print(" MANUAL COMMAND TEST")
    print("="*80)
    print("\nTesting:")
    print("- /character [name] command")
    print("- /beat [text] command")
    print("- /scene [number] [title] command")
    print("="*80)

    async with aiohttp.ClientSession() as session:
        for turn in CONVERSATION:
            await send_message(session, turn["msg"], turn["desc"])
            await asyncio.sleep(1.5)

        # Check final state
        print(f"\n{'='*80}")
        print(" FINAL STATE VERIFICATION")
        print(f"{'='*80}\n")

        async with session.get("http://localhost:8888/state") as response:
            state = await response.json()

            fields = state.get("fields", {})
            locked = state.get("locked", {})

            # Verify title locked
            print(f"✓ Title: {fields.get('title')} {'✅ LOCKED' if locked.get('title') else '❌ NOT LOCKED'}")

            # Verify logline locked
            logline = fields.get('logline', '')
            print(f"✓ Logline: {logline[:60] if logline else 'None'}... {'✅ LOCKED' if locked.get('logline') else '❌ NOT LOCKED'}")

            # Verify characters tracked via manual commands
            characters = fields.get('characters', [])
            print(f"\n👥 CHARACTERS ({len(characters)} tracked via /character commands):")
            for char in characters:
                print(f"\n   {char.get('name')} ({char.get('role')}):")
                if char.get('age'):
                    print(f"      Age: {char.get('age')}")
                if char.get('personality'):
                    print(f"      Personality: {char.get('personality')}")
                if char.get('flaw'):
                    print(f"      Flaw: {char.get('flaw')}")
                if char.get('backstory'):
                    print(f"      Backstory: {char.get('backstory')}")

            # Verify outline beats via manual commands
            outline = fields.get('outline', [])
            print(f"\n📖 OUTLINE BEATS ({len(outline)} tracked via /beat commands):")
            for i, beat in enumerate(outline, 1):
                print(f"   {i}. {beat}")

            # Verify scenes via manual commands
            beats = fields.get('beats', [])
            print(f"\n🎬 SCENES ({len(beats)} tracked via /scene commands):")
            for scene in beats:
                print(f"   #{scene.get('number')}: {scene.get('title')}")
                if scene.get('description'):
                    print(f"      {scene.get('description')}")

            # Summary
            print(f"\n{'='*80}")
            print(" TEST SUMMARY")
            print(f"{'='*80}")

            results = {}
            results['title_locked'] = locked.get('title', False)
            results['logline_locked'] = locked.get('logline', False)
            results['characters_tracked'] = len(characters) >= 2
            results['beats_tracked'] = len(outline) >= 1
            results['scenes_tracked'] = len(beats) >= 1

            for key, passed in results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} - {key}")

            passed_count = sum(1 for v in results.values() if v)
            total = len(results)

            print(f"\n📊 RESULTS: {passed_count}/{total} checks passed")

            if passed_count == total:
                print(f"\n🎉 ALL MANUAL COMMANDS WORKING!")
            elif passed_count >= total - 1:
                print(f"\n✅ MOSTLY WORKING")
            else:
                print(f"\n⚠️  NEEDS ATTENTION")

            print(f"\n{'='*80}")

            return passed_count == total

if __name__ == "__main__":
    try:
        success = asyncio.run(test_manual_commands())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
