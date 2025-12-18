"""Test directive system with a different romcom concept"""
import asyncio
import aiohttp
import json

# Different romcom: Wedding photographer meets wedding planner
CONVERSATION = [
    {
        "msg": "A cynical wedding photographer who stopped believing in love after her own engagement fell apart keeps running into this ridiculously optimistic wedding planner at every job. He believes in soulmates and happy endings, she thinks it's all a performance. They clash constantly but keep getting booked for the same weddings. Eventually they're forced to work together on a massive society wedding in the Hamptons over a long weekend.",
        "desc": "Initial pitch - wedding photographer/planner"
    },
    {
        "msg": "I'm thinking 'Say I Don't' for the title",
        "desc": "User suggests title"
    },
    {
        "msg": "Yes, lock it",
        "desc": "User confirms title"
    },
    {
        "msg": "Perfect logline",
        "desc": "User approves logline"
    },
    {
        "msg": "Yes",
        "desc": "User confirms logline lock"
    }
]

async def send_message(session, msg, desc):
    """Send message and return response"""
    url = "http://localhost:8888/chat"

    print(f"\n{'='*70}")
    print(f"USER ({desc}): {msg[:60]}{'...' if len(msg) > 60 else ''}")
    print(f"{'='*70}\n")

    async with session.post(url, json={"message": msg}) as response:
        if response.status != 200:
            print(f"❌ Error: {await response.text()}")
            return ""

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

        print(f"\n{'='*70}")

        # Check for asking
        if "should i lock" in full_response.lower():
            print("🔔 SYD ASKING TO LOCK")

        # Check for directive
        if "[DIRECTIVE:" in full_response:
            print("📝 DIRECTIVE EMITTED")

        return full_response

async def test_new_romcom():
    """Test with wedding photographer/planner story"""
    print("="*70)
    print("TESTING NEW ROMCOM: Wedding Photographer + Planner")
    print("="*70)

    async with aiohttp.ClientSession() as session:
        for turn in CONVERSATION:
            await send_message(session, turn["msg"], turn["desc"])
            await asyncio.sleep(1)

        # Check final state
        print(f"\n{'='*70}")
        print("FINAL STATE")
        print(f"{'='*70}")

        async with session.get("http://localhost:8888/state") as response:
            state = await response.json()

            fields = state.get("fields", {})
            locked = state.get("locked", {})

            print(f"\n✓ Title: {fields.get('title')} {'[LOCKED]' if locked.get('title') else '[NOT LOCKED]'}")
            print(f"✓ Logline: {fields.get('logline', '')[:60] if fields.get('logline') else 'None'}... {'[LOCKED]' if locked.get('logline') else '[NOT LOCKED]'}")
            print(f"✓ Characters: {len(fields.get('characters', []))} tracked")

            for char in fields.get('characters', []):
                print(f"   - {char.get('name')} ({char.get('role')})")

            print(f"\n{'='*70}")

            if locked.get('title') and locked.get('logline'):
                print("✅ SUCCESS: Different romcom tracked successfully!")
                print(f"   Story: Wedding photographer/planner")
                print(f"   Title: {fields.get('title')}")
                print(f"   Characters: {len(fields.get('characters', []))} tracked")
            else:
                print("❌ FAIL: Not everything locked")

if __name__ == "__main__":
    try:
        asyncio.run(test_new_romcom())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
