"""Test database persistence for title, logline, and characters"""
import asyncio
import aiohttp
import json
import sqlite3
from pathlib import Path

# Test database path
TEST_DB = Path("./test_project.db")

async def run_conversation():
    """Run a conversation that locks title, logline, and characters"""
    url = "http://localhost:8888/chat"

    messages = [
        "Maude and Ivy are roommates in DC. They both meet and click with Lars at a bar, but he only texts Ivy back. For the first time, Ivy decides not to step aside for her more charismatic friend.",
        "Yes, 'Room for One' is perfect. Lock that title.",
        "Perfect logline. Lock it in."
    ]

    async with aiohttp.ClientSession() as session:
        for i, msg in enumerate(messages, 1):
            print(f"\n{'='*60}")
            print(f"Turn {i}: {msg[:50]}...")
            print(f"{'='*60}")

            async with session.post(url, json={"message": msg}) as response:
                if response.status != 200:
                    print(f"❌ Error: {await response.text()}")
                    return False

                # Consume response
                async for line in response.content:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if data.get('type') == 'chunk':
                                print(data.get('content', ''), end='', flush=True)
                        except json.JSONDecodeError:
                            pass

            print(f"\n{'='*60}\n")
            await asyncio.sleep(1)

    return True

async def save_to_database():
    """Call the save endpoint"""
    url = "http://localhost:8888/save"

    async with aiohttp.ClientSession() as session:
        print("\n" + "="*60)
        print("SAVING TO DATABASE")
        print("="*60)

        async with session.post(url, json={"db_path": str(TEST_DB)}) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Saved! Project ID: {result.get('project_id')}")
                return True
            else:
                print(f"❌ Save failed: {await response.text()}")
                return False

def verify_database():
    """Verify data was saved correctly"""
    print("\n" + "="*60)
    print("VERIFYING DATABASE")
    print("="*60)

    if not TEST_DB.exists():
        print("❌ Database file doesn't exist")
        return False

    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    success = True

    # Check project
    cursor.execute("SELECT * FROM projects")
    project = cursor.fetchone()
    if project:
        print(f"\n✅ PROJECT:")
        print(f"   Name: {project['name']}")
        if project['name'] != "Room for One":
            print(f"   ❌ Expected 'Room for One', got '{project['name']}'")
            success = False
    else:
        print("❌ No project found")
        success = False

    # Check writer notes
    cursor.execute("SELECT * FROM writer_notes")
    notes = cursor.fetchone()
    if notes:
        print(f"\n✅ WRITER NOTES:")
        print(f"   Logline: {notes['logline'][:80]}...")
        print(f"   Tone: {notes['tone']}")
        if not notes['logline']:
            print("   ❌ Logline is empty")
            success = False
    else:
        print("❌ No writer notes found")
        success = False

    # Check characters
    cursor.execute("SELECT * FROM characters")
    characters = cursor.fetchall()
    if characters:
        print(f"\n✅ CHARACTERS ({len(characters)} found):")
        for char in characters:
            print(f"   - {char['name']} ({char['role']})")
            print(f"     {char['description'][:60]}...")

        # Verify we have at least 2 characters
        if len(characters) < 2:
            print(f"   ⚠️  Expected at least 2 characters, got {len(characters)}")

        # Verify we have Ivy and Maude
        names = [c['name'] for c in characters]
        if 'Ivy' not in names:
            print("   ❌ Missing character: Ivy")
            success = False
        if 'Maude' not in names:
            print("   ❌ Missing character: Maude")
            success = False
    else:
        print("❌ No characters found")
        success = False

    conn.close()

    print("\n" + "="*60)
    if success:
        print("✅ DATABASE PERSISTENCE TEST PASSED")
    else:
        print("❌ DATABASE PERSISTENCE TEST FAILED")
    print("="*60)

    return success

async def main():
    """Run complete database persistence test"""
    print("="*60)
    print("DATABASE PERSISTENCE TEST")
    print("Testing: Title, Logline, Characters")
    print("="*60)

    # Clean up old test database
    if TEST_DB.exists():
        TEST_DB.unlink()
        print(f"\n🗑️  Cleaned up old test database")

    # Run conversation
    if not await run_conversation():
        print("\n❌ Conversation failed")
        return

    # Save to database
    if not await save_to_database():
        print("\n❌ Database save failed")
        return

    # Verify
    verify_database()

    # Clean up
    print(f"\n🗑️  Cleaning up test database...")
    if TEST_DB.exists():
        TEST_DB.unlink()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
