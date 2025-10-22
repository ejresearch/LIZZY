# AI Block Composer - Natural Language to Prompts ✨

**Just type what you're thinking - the AI builds the blocks for you!**

---

## 🎯 The Problem It Solves

**Before (Manual):**
```python
blocks = [
    SceneBlock(scene_number=4),
    CharacterBiosBlock(),
    ScriptsQueryBlock(query="disappointment scenes"),
]
prompt = assemble_prompt(blocks, project_name="my_project")
```

**After (Natural Language):**
```python
composer = AIBlockComposer("my_project")
result = await composer.compose(
    "Jenny in scene 4 dealing with disappointment, check scripts bucket"
)
# AI automatically builds the same blocks!
```

---

## 🚀 Quick Start

### CLI (Interactive)

```bash
python3 ai_composer_cli.py
```

Then just type what you're thinking:
- "Help me with scene 1, what do books say about openings?"
- "Jenny dealing with disappointment in scene 4, check scripts"
- "Stuck on the wedding scene, need all three experts"

### CLI (One-Shot)

```bash
python3 ai_composer_cli.py -q "Help with scene 5, check books bucket"
```

### Python API

```python
from lizzy.prompt_studio import AIBlockComposer

composer = AIBlockComposer("the_proposal_2_0")

result = await composer.compose(
    "I'm stuck on scene 12, what do the plays say about dramatic confessions?"
)

print(result.prompt)  # Fully assembled prompt ready to use!
```

---

## 🧠 How It Works

### 3-Step Process

```
User Input (Natural Language)
        ↓
   AI Parser (GPT-4o-mini)
        ↓
   SQL Lookup (Find actual scene/character data)
        ↓
   Block Builder (Create blocks)
        ↓
   Prompt Engine (Assemble prompt)
        ↓
   Final Prompt (Ready to use!)
```

### Example Flow

**You say:**
> "Jenny in scene 4 dealing with disappointment, check scripts bucket"

**AI Parser extracts:**
```json
{
  "scene_reference": "scene 4",
  "character_names": ["Jenny"],
  "topic": "dealing with disappointment",
  "buckets": ["scripts"],
  "intent": "get_inspiration"
}
```

**SQL Lookup finds:**
- Scene 4 exists → scene_number = 4
- Character "Jenny" exists → gets full bio

**Block Builder creates:**
```python
[
    SectionHeaderBlock(title="SCENE 4"),
    SceneBlock(scene_number=4),  # ← Auto-injected from SQL!
    SectionHeaderBlock(title="CHARACTERS"),
    TextBlock("Jenny: [full bio]"),  # ← Auto-injected from SQL!
    SectionHeaderBlock(title="WORKING ON"),
    TextBlock("dealing with disappointment"),
    SectionHeaderBlock(title="EXPERT GUIDANCE"),
    ScriptsQueryBlock(query="dealing with disappointment focusing on characters: Jenny"),
]
```

**Prompt Engine executes blocks:**
- SceneBlock queries SQL again and injects all scene data
- ScriptsQueryBlock queries RAG bucket
- All outputs combined into final prompt

**Result:** Complete prompt with SQL + RAG data!

---

## 📝 What the AI Can Detect

### Scene References
- "scene 4" → Finds scene 4
- "act 1 scene 4" → Extracts scene 4
- "the wedding scene" → Fuzzy matches on title
- "scene 12" → Exact match

### Character Names
- "Jenny" → Finds character "Jenny"
- "Mark and Emma" → Finds both characters
- Any character name mentioned

### Topics
- "dealing with disappointment"
- "romantic tension"
- "dramatic confession"
- Any concept you're working on

### Buckets
- "books" / "books bucket" → BooksQueryBlock
- "plays" / "plays bucket" → PlaysQueryBlock
- "scripts" / "scripts bucket" → ScriptsQueryBlock
- "all three experts" / "all buckets" → MultiExpertQueryBlock

### Intent
- get_inspiration
- analyze_scene
- get_feedback
- explore_idea

### Context Requests
- "with context" → Adds PreviousSceneBlock + NextSceneBlock
- "show surrounding scenes" → Includes adjacent scenes

---

## 🎓 Example Queries

### Example 1: Scene + Expert

**Input:**
> "Help me with scene 1, what do books say about romantic comedy openings?"

**AI Detects:**
- Scene: 1
- Bucket: books
- Topic: romantic comedy openings

**Blocks Created:**
- SceneBlock(1)
- BooksQueryBlock("romantic comedy openings")

**Result:** Scene 1 data + Books expert guidance

---

### Example 2: Character Focus

**Input:**
> "Jenny in scene 4 dealing with disappointment, check scripts"

**AI Detects:**
- Scene: 4
- Character: Jenny
- Topic: dealing with disappointment
- Bucket: scripts

**Blocks Created:**
- SceneBlock(4)
- TextBlock("Character: Jenny...")
- ScriptsQueryBlock("dealing with disappointment focusing on Jenny")

**Result:** Scene 4 + Jenny bio + Scripts expert on disappointment

---

### Example 3: Multi-Expert

**Input:**
> "I'm stuck on act 2 scene 12, need all three experts"

**AI Detects:**
- Scene: 12
- Buckets: all
- Intent: get_inspiration

**Blocks Created:**
- SceneBlock(12)
- MultiExpertQueryBlock("general screenplay writing advice")

**Result:** Scene 12 + All 3 experts (books, plays, scripts)

---

### Example 4: Just RAG Query

**Input:**
> "What do the plays bucket say about dramatic confessions?"

**AI Detects:**
- Bucket: plays
- Topic: dramatic confessions
- Intent: get_inspiration

**Blocks Created:**
- PlaysQueryBlock("dramatic confessions")

**Result:** Just the plays expert response

---

## 🔧 API Reference

### AIBlockComposer

```python
class AIBlockComposer:
    def __init__(self, project_name: str):
        """Initialize composer for a project"""
        pass

    async def compose(self, user_input: str) -> PromptResult:
        """
        Compose blocks from natural language.

        Returns:
            PromptResult with:
                - prompt: Assembled prompt string
                - parsed_entities: What the AI detected
                - blocks_used: Which blocks were created
                - metadata: Execution stats
        """
        pass

    async def compose_prompt_only(self, user_input: str) -> str:
        """Quick helper that just returns the prompt string"""
        pass
```

### EntityParser

```python
class EntityParser:
    async def parse(self, user_input: str, project_name: str) -> Dict:
        """
        Parse natural language to extract entities.

        Returns:
            {
                "scene_reference": str or None,
                "character_names": List[str] or None,
                "topic": str or None,
                "buckets": List[str] or None,
                "include_context": bool,
                "intent": str
            }
        """
        pass
```

### SQLLookup

```python
class SQLLookup:
    def find_scene_number(self, scene_reference: str) -> Optional[int]:
        """Find scene number from natural language reference"""
        pass

    def find_characters(self, character_names: List[str]) -> List[Dict]:
        """Find character data from names"""
        pass

    def get_all_scene_titles(self) -> List[Dict]:
        """Get all scenes (for fuzzy matching)"""
        pass
```

### BlockBuilder

```python
class BlockBuilder:
    def build(self, parsed: Dict) -> List[Block]:
        """Build blocks from parsed entities"""
        pass
```

---

## 🎨 CLI Commands

### Interactive Mode (Default)

```bash
python3 ai_composer_cli.py

# Then type naturally:
> Help me with scene 1, check books
> Jenny dealing with disappointment, scripts bucket
> Show me scene 5 with context, all experts
```

### One-Shot Query

```bash
python3 ai_composer_cli.py -q "YOUR QUERY HERE"
```

### Run Examples

```bash
python3 ai_composer_cli.py --examples
```

### Specify Project

```bash
python3 ai_composer_cli.py -p "my_project_name"
```

### Help

```bash
python3 ai_composer_cli.py --help
```

---

## 🧪 Testing

### Test 1: Scene Lookup

```bash
python3 ai_composer_cli.py -q "Show me scene 1"
```

**Expected:** Scene 1 data injected from SQL

### Test 2: Character + Scene

```bash
python3 ai_composer_cli.py -q "Jenny in scene 4"
```

**Expected:** Scene 4 data + Jenny's character bio

### Test 3: RAG Query

```bash
python3 ai_composer_cli.py -q "What do books say about openings?"
```

**Expected:** BooksQueryBlock with query "openings"

### Test 4: Multi-Expert

```bash
python3 ai_composer_cli.py -q "Scene 1, all three experts"
```

**Expected:** Scene 1 + MultiExpertQueryBlock

---

## 📊 Performance

### Typical Times

- **AI Parsing**: ~500-1000ms (GPT-4o-mini call)
- **SQL Lookup**: <1ms
- **Block Building**: <1ms
- **Block Execution**: 1-5ms (without RAG), 500-2000ms (with RAG)

**Total**: ~1-3 seconds including RAG queries

### Cost

- **AI Parsing**: ~$0.0001 per query (GPT-4o-mini is cheap!)
- **RAG Queries**: ~$0.001 per query (depends on bucket size)

**Very affordable for interactive use!**

---

## 🎯 Use Cases

### Use Case 1: Quick Scene Lookup

**Without AI Composer:**
```python
blocks = [SceneBlock(scene_number=5)]
prompt = assemble_prompt(blocks, "my_project")
```

**With AI Composer:**
```bash
> Show me scene 5
```

**Benefit:** Faster, natural

---

### Use Case 2: Expert Consultation

**Without AI Composer:**
```python
blocks = [
    SceneBlock(5),
    BooksQueryBlock("romantic tension techniques"),
]
```

**With AI Composer:**
```bash
> Scene 5, what do books say about romantic tension?
```

**Benefit:** Natural language, AI builds query

---

### Use Case 3: Character Analysis

**Without AI Composer:**
```python
blocks = [
    CharacterBiosBlock(),
    PlaysQueryBlock("character dynamics"),
]
```

**With AI Composer:**
```bash
> Tell me about the characters, check plays for dynamics
```

**Benefit:** Simpler, conversational

---

## 💡 Pro Tips

### 1. Be Specific About Scenes

✅ Good: "scene 4", "act 2 scene 12"
❌ Vague: "that scene", "the other one"

### 2. Mention Buckets Explicitly

✅ Good: "check scripts bucket", "what do plays say"
❌ Vague: "get some advice"

### 3. State Your Topic

✅ Good: "dealing with disappointment", "romantic tension"
❌ Vague: "help with this"

### 4. Use Natural Language

✅ Good: "I'm stuck on scene 5, need books expert"
✅ Good: "Jenny in scene 4, what do scripts say?"
✅ Good: "Show me the wedding scene with all experts"

You don't need to be formal - just type what you're thinking!

---

## 🔮 Future Enhancements

### Planned Features

1. **Context Memory** - Remember previous queries in session
2. **Smart Suggestions** - AI suggests related scenes/characters
3. **Query History** - Save and rerun previous queries
4. **Custom Prompts** - Train on your writing style
5. **Export to Code** - Convert natural language to Python blocks

---

## 🏗️ Architecture

### Components

```
lizzy/prompt_studio/ai_composer.py
├── EntityParser      # LLM-based entity extraction
├── SQLLookup         # Database queries
├── BlockBuilder      # Converts entities → blocks
└── AIBlockComposer   # Main orchestrator
```

### Dependencies

- **OpenAI API** - For entity parsing (GPT-4o-mini)
- **SQLite** - For scene/character lookup
- **Prompt Studio** - For block execution
- **LightRAG** - For RAG queries (if buckets exist)

---

## 📚 Related Documentation

- **PROMPT_STUDIO_ARCHITECTURE.md** - Block system design
- **PROMPT_STUDIO_IMPLEMENTATION.md** - Implementation details
- **Prompt Studio README** - Block API reference

---

## ✅ Status

**Current**: ✅ Fully Implemented and Working

**Tested With:**
- ✅ Scene lookups
- ✅ Character detection
- ✅ Bucket selection
- ✅ Topic extraction
- ✅ Multi-expert queries

**Next Steps:**
- Add context memory
- Add query history
- Improve fuzzy matching
- Add more examples

---

## 🎉 Summary

**AI Block Composer** turns natural language into prompts automatically:

1. **You type** what you're thinking
2. **AI parses** and extracts entities
3. **SQL looks up** actual scene/character data
4. **Blocks auto-build** and execute
5. **You get** a complete prompt with all data injected

**No more manual block building - just describe what you want!**

---

**Examples:**

```bash
# Interactive
python3 ai_composer_cli.py

# One-shot
python3 ai_composer_cli.py -q "Jenny in scene 4, check scripts"

# Run examples
python3 ai_composer_cli.py --examples
```

---

**It's like having a conversation with your screenplay data!**
