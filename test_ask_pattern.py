"""Test the 'AI asks permission' pattern for locking fields"""
import asyncio
import aiohttp
import json

CONVERSATION = [
    {
        "user": "Two roommates in DC both fall for the same guy. Title: 'Room for One'",
        "expect": "AI should ask: 'Should I lock this title?'",
        "look_for": ["Should I lock", "lock this title", "save", "confirm"]
    },
    {
        "user": "Yes",
        "expect": "AI should emit lock_title directive",
        "look_for": ["[DIRECTIVE:lock_title", "locked", "✓"]
    }
]

async def test_ask_pattern():
    """Test AI asking permission before locking"""
    url = "http://localhost:8888/chat"

    print("="*60)
    print("TESTING: AI ASKS PERMISSION PATTERN")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        for i, turn in enumerate(CONVERSATION, 1):
            print(f"\n{'='*60}")
            print(f"TURN {i}: {turn['user']}")
            print(f"EXPECT: {turn['expect']}")
            print(f"{'='*60}\n")

            async with session.post(url, json={"message": turn["user"]}) as response:
                if response.status != 200:
                    print(f"❌ Error: {await response.text()}")
                    return False

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

                print(f"\n\n{'='*60}")

                # Check expectations
                found = []
                for phrase in turn["look_for"]:
                    if phrase.lower() in full_response.lower():
                        found.append(phrase)

                if found:
                    print(f"✅ Found expected patterns: {', '.join(found)}")
                else:
                    print(f"⚠️  Expected to find one of: {turn['look_for']}")
                    print(f"   Got: {full_response[:100]}...")

                await asyncio.sleep(1)

    # Check final state
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8888/state") as response:
            state = await response.json()

            print(f"\n{'='*60}")
            print("FINAL STATE")
            print(f"{'='*60}")
            print(f"Title: {state['fields'].get('title')}")
            print(f"Title Locked: {state['locked'].get('title')}")

            if state['locked'].get('title'):
                print("\n✅ SUCCESS: AI asked permission and locked title!")
            else:
                print("\n⚠️  Title not locked - AI may need more explicit asking")

if __name__ == "__main__":
    try:
        asyncio.run(test_ask_pattern())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
