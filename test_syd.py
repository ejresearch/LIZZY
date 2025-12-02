"""Test Syd conversation with Maude/Ivy story"""
import asyncio
import aiohttp
import json

TEST_MESSAGE = """Maude and Ivy are in their early 20s living in DC. Maude is from a well off family - mom did PR for a smattering of public figures so her 'entry level job' allows her a lifestyle that transcends her paycheck. Ivy is in her second year of grad school and outside of that, she's pretty nonchalant about everything - Maude decorated their whole apartment leaving out Ivy's one piece of decor and she couldn't care less. Despite their differences, they've had a solid friendship and chill living situation, almost like sisters. Ivy rarely joins Maude for a night out, but this quarter she's finished finals early and gotten great scores so she joins her and meets Lars who she instantly hits it off with. They chat for an hour, exchange numbers, and then she doesn't see him the rest of the night. The next morning, Ivy and Maude are unloading groceries or making breakfast and they chat about their night where they slowly realize they both met and felt like they clicked with Lars. At that point they'd either both texted him and he'd only responded to Ivy or like only texted Ivy. This makes Maude noticeably jealous and while Ivy would usually give in, for once, she thinks this is someone/something she really wants."""

async def test_chat():
    url = "http://localhost:8888/chat"

    print("=" * 60)
    print("TESTING SYD - PHASE 1: Just Talk")
    print("=" * 60)
    print(f"\nSending message ({len(TEST_MESSAGE)} chars)...")
    print(f"First 80 chars: {TEST_MESSAGE[:80]}...")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"message": TEST_MESSAGE}) as response:
            print(f"\nResponse status: {response.status}")

            if response.status != 200:
                print(f"ERROR: {await response.text()}")
                return

            print("\nStreaming response:")
            print("-" * 60)

            full_response = ""
            chunk_count = 0

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
                            chunk_count += 1
                        elif data.get('type') == 'state':
                            # State update at end
                            pass
                    except json.JSONDecodeError:
                        pass

            print("\n" + "-" * 60)
            print(f"\n✅ Response complete!")
            print(f"   Chunks received: {chunk_count}")
            print(f"   Total chars: {len(full_response)}")
            print(f"   Words: {len(full_response.split())}")

            if len(full_response) > 0:
                print("\n✅ TEXT GENERATION WORKING!")
            else:
                print("\n❌ NO TEXT RECEIVED")

if __name__ == "__main__":
    try:
        asyncio.run(test_chat())
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
