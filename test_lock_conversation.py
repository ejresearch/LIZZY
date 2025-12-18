"""Test natural conversation with lock confirmations"""
import asyncio
import aiohttp
import json

CONVERSATION = [
    {
        "msg": """Maude and Ivy are in their early 20s living in DC. Maude is from a well off family - mom did PR for a smattering of public figures so her 'entry level job' allows her a lifestyle that transcends her paycheck. Ivy is in her second year of grad school and outside of that, she's pretty nonchalant about everything - Maude decorated their whole apartment leaving out Ivy's one piece of decor and she couldn't care less. Despite their differences, they've had a solid friendship and chill living situation, almost like sisters. Ivy rarely joins Maude for a night out, but this quarter she's finished finals early and gotten great scores so she joins her and meets Lars who she instantly hits it off with. They chat for an hour, exchange numbers, and then she doesn't see him the rest of the night. The next morning, Ivy and Maude are unloading groceries or making breakfast and they chat about their night where they slowly realize they both met and felt like they clicked with Lars. At that point they'd either both texted him and he'd only responded to Ivy or like only texted Ivy. This makes Maude noticeably jealous and while Ivy would usually give in, for once, she thinks this is someone/something she really wants.""",
        "desc": "Initial pitch"
    },
    {
        "msg": "I like 'Room for One' as the title",
        "desc": "User mentions title (AI should ask to lock)"
    },
    {
        "msg": "Yes, lock it",
        "desc": "User confirms (AI should emit directive)"
    },
    {
        "msg": "That logline is perfect",
        "desc": "User likes logline (AI should ask to lock)"
    },
    {
        "msg": "Yes",
        "desc": "User confirms logline (AI should emit directive)"
    }
]

async def send_and_print(session, msg, desc):
    """Send message and print response"""
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

        # Highlight if Syd is asking to lock
        if "should i lock" in full_response.lower():
            print("\n🔔 SYD IS ASKING TO LOCK SOMETHING")

        # Highlight if directive was emitted
        if "[DIRECTIVE:" in full_response:
            print("\n📝 DIRECTIVE EMITTED (will be stripped from user view)")

        return full_response

async def test_conversation():
    """Run full conversation testing lock pattern"""
    print("="*70)
    print("TESTING: Natural Lock Conversation Pattern")
    print("="*70)

    async with aiohttp.ClientSession() as session:
        for turn in CONVERSATION:
            response = await send_and_print(session, turn["msg"], turn["desc"])
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
            print(f"✓ Logline: {fields.get('logline', '')[:60]}... {'[LOCKED]' if locked.get('logline') else '[NOT LOCKED]'}")
            print(f"✓ Characters: {len(fields.get('characters', []))} tracked")

            # Summary
            print(f"\n{'='*70}")

            if locked.get('title') and locked.get('logline'):
                print("✅ SUCCESS: Title and logline locked via conversation!")
            elif locked.get('title'):
                print("⚠️  PARTIAL: Title locked, but logline not locked")
            else:
                print("❌ FAIL: Nothing locked - AI may not be asking")

if __name__ == "__main__":
    try:
        asyncio.run(test_conversation())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
