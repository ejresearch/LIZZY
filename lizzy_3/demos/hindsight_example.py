"""
Hindsight Memory Demo for lizzy_3

This demo shows how Hindsight's memory system works for Syd,
the AI screenwriting partner in lizzy_3.

Hindsight provides three core operations:
  - RETAIN: Store memories (facts, experiences, opinions, observations)
  - RECALL: Retrieve relevant memories via semantic search
  - REFLECT: Generate contextual responses using memories + LLM

Memory Types:
  - World: Facts about the environment ("Emma is the protagonist")
  - Experience: The agent's own encounters ("User liked the breakfast scene idea")
  - Opinion: Beliefs with confidence ("User prefers witty banter over slapstick")
  - Observation: Derived insights from reflection

To run this demo:
  1. Start Hindsight server: hindsight-api --port 8888
  2. Run this script: python demos/hindsight_example.py

Requirements:
  - hindsight-all package installed
  - OPENAI_API_KEY set (for LLM in reflect)
"""

import sys
import time

# Check if Hindsight client is available
try:
    from hindsight_client import Hindsight, RecallResponse
except ImportError:
    print("ERROR: hindsight-all not installed")
    print("Install with: pip install hindsight-all")
    sys.exit(1)


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_step(step: str, description: str):
    """Print a numbered step."""
    print(f"\n[{step}] {description}")
    print("-" * 40)


def main():
    """Run the Hindsight demo."""

    # Configuration
    HINDSIGHT_URL = "http://localhost:8889"  # Note: uses /v1/default/* paths internally
    BANK_ID = "syd-demo"  # Memory bank for Syd

    print_header("HINDSIGHT MEMORY DEMO")
    print(f"Server: {HINDSIGHT_URL}")
    print(f"Bank ID: {BANK_ID}")

    # Initialize client
    try:
        client = Hindsight(base_url=HINDSIGHT_URL)
        print("\nConnected to Hindsight server.")
    except Exception as e:
        print(f"\nERROR: Could not connect to Hindsight server at {HINDSIGHT_URL}")
        print(f"Start server with: hindsight-api --port 8888")
        print(f"Details: {e}")
        sys.exit(1)

    # =========================================================================
    # STEP 1: Create a memory bank with Syd's personality
    # =========================================================================
    print_step("1", "CREATE MEMORY BANK")

    try:
        bank = client.create_bank(
            bank_id=BANK_ID,
            name="Syd",
            background="""
            You are Syd, a creative partner for screenwriters specializing in romantic comedies.
            You're encouraging, insightful, and always focused on helping writers develop their stories.
            You remember past conversations and use that context to provide better assistance.
            """,
            disposition={
                "openness": 0.9,      # Creative, imaginative
                "conscientiousness": 0.7,  # Organized but flexible
                "extraversion": 0.8,  # Enthusiastic, engaging
                "agreeableness": 0.85,  # Supportive, encouraging
                "neuroticism": 0.2,   # Calm, stable
            }
        )
        print(f"Created bank: {bank.name}")
        print(f"Background: {bank.background[:80]}...")
    except Exception as e:
        print(f"Note: {e}")
        print("(Bank may already exist, continuing...)")

    # =========================================================================
    # STEP 2: RETAIN - Store memories from a brainstorming session
    # =========================================================================
    print_step("2", "RETAIN - Store memories")

    # Simulate memories from a screenwriting session
    memories = [
        # World facts (about the project)
        {
            "content": "The screenplay is titled 'Second Chances' - a romantic comedy set in Portland.",
            "context": "Project setup"
        },
        {
            "content": "Emma Chen is the protagonist - a 32-year-old divorce attorney who doesn't believe in love.",
            "context": "Character creation"
        },
        {
            "content": "The love interest is Ben, a romantic wedding planner who's Emma's new neighbor.",
            "context": "Character creation"
        },
        {
            "content": "The central irony: a divorce lawyer falling for a wedding planner.",
            "context": "Thematic discussion"
        },

        # Experiences (what happened in sessions)
        {
            "content": "User got excited when we discussed the 'fake dating for work event' trope as a possible B-plot.",
            "context": "Brainstorming session"
        },
        {
            "content": "User mentioned they love the breakfast scene in 'When Harry Met Sally' - want similar banter.",
            "context": "Reference discussion"
        },

        # Opinions/preferences discovered
        {
            "content": "User prefers witty, rapid-fire dialogue over physical comedy.",
            "context": "Style preference"
        },
        {
            "content": "User wants to avoid the 'big misunderstanding' trope - prefers earned conflict.",
            "context": "Story preference"
        },
    ]

    # Store each memory
    for mem in memories:
        result = client.retain(
            bank_id=BANK_ID,
            content=mem["content"],
            context=mem["context"],
        )
        print(f"  Stored: {mem['content'][:50]}...")

    print(f"\nTotal memories stored: {len(memories)}")

    # Give it a moment to process
    time.sleep(1)

    # =========================================================================
    # STEP 3: RECALL - Retrieve relevant memories
    # =========================================================================
    print_step("3", "RECALL - Retrieve relevant memories")

    queries = [
        "Who is the main character?",
        "What dialogue style does the user prefer?",
        "What tropes should we avoid?",
        "What movie references did the user mention?",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        try:
            response = client.recall(
                bank_id=BANK_ID,
                query=query,
                max_tokens=500,
                budget="mid",
            )

            if response.results:
                for r in response.results[:2]:  # Show top 2 results
                    print(f"  [{r.type}] {r.text[:70]}...")
            else:
                print("  (no results)")
        except Exception as e:
            print(f"  Error: {e}")

    # =========================================================================
    # STEP 4: REFLECT - Generate contextual response using memories
    # =========================================================================
    print_step("4", "REFLECT - Generate contextual response")

    reflect_queries = [
        "What do we know about Emma's character so far?",
        "What kind of dialogue should I write for the meet-cute scene?",
        "Based on our conversations, what scene should we work on next?",
    ]

    for query in reflect_queries:
        print(f"\nQuery: '{query}'")
        try:
            response = client.reflect(
                bank_id=BANK_ID,
                query=query,
                budget="mid",
            )

            print(f"\nSyd's response:")
            # Handle both string and object responses
            if hasattr(response, 'text'):
                print(f"  {response.text}")
            elif hasattr(response, 'answer'):
                print(f"  {response.answer}")
            else:
                print(f"  {response}")

            # Show which facts were used
            if hasattr(response, 'facts') and response.facts:
                print(f"\n  Based on {len(response.facts)} memories")

        except Exception as e:
            print(f"  Error: {e}")

    # =========================================================================
    # STEP 5: List all memories in the bank
    # =========================================================================
    print_step("5", "LIST - View all stored memories")

    try:
        all_memories = client.list_memories(
            bank_id=BANK_ID,
            limit=20
        )

        if hasattr(all_memories, 'items') and all_memories.items:
            print(f"Total memories in bank: {len(all_memories.items)}")
            for mem in all_memories.items[:5]:
                mem_type = getattr(mem, 'type', 'unknown')
                mem_text = getattr(mem, 'text', str(mem))[:60]
                print(f"  [{mem_type}] {mem_text}...")
        else:
            print("No memories found or different response format")
            print(f"Response: {all_memories}")

    except Exception as e:
        print(f"Error listing memories: {e}")

    # Cleanup
    client.close()

    print_header("DEMO COMPLETE")
    print("""
This demo showed how Hindsight enables Syd to:

1. Remember project details (characters, settings, themes)
2. Track user preferences (dialogue style, trope preferences)
3. Recall relevant context when answering questions
4. Generate informed responses based on accumulated knowledge

In lizzy_3, this means Syd can maintain continuity across the entire
screenwriting process - from initial ideation through the finished script.
    """)


if __name__ == "__main__":
    main()
