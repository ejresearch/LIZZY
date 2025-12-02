# Lizzy Architecture: Directives & Commands

Lizzy (via Syd, the chatbot persona) is a conversational AI for brainstorming romantic comedies. It has two mechanisms for storing and organizing ideas during conversation.

---

## Core Model

```
┌─────────────────────────────────────────────────────────────┐
│                         SYD (Chatbot)                        │
│                                                              │
│  Natural conversation about romcom ideas, characters, plot  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│      DIRECTIVES          │    │       COMMANDS           │
│   (AI-initiated)         │    │    (User-initiated)      │
│                          │    │                          │
│ Syd embeds these in      │    │ User types /command to   │
│ responses automatically  │    │ manually trigger actions │
│ when ideas crystallize   │    │                          │
│                          │    │                          │
│ User never sees them     │    │ Explicit user control    │
│ (stripped on frontend)   │    │                          │
└──────────────────────────┘    └──────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
              ┌──────────────────────────────┐
              │      SESSION STATE           │
              │                              │
              │  • title (locked/pending)    │
              │  • logline (locked/pending)  │
              │  • characters[]              │
              │  • beats[] (30 scenes)       │
              │  • outline[] (5-8 moments)   │
              │  • notebook[] (ideas)        │
              │  • theme, tone, comps        │
              └──────────────────────────────┘
                              │
                              ▼
              ┌──────────────────────────────┐
              │        DATABASE              │
              │  (SQLite via save action)    │
              └──────────────────────────────┘
```

---

## Directives (AI-Initiated)

Directives are embedded metadata that Syd includes in responses. They're invisible to users (stripped by the frontend) but trigger state updates.

### Syntax
```
[DIRECTIVE:action|param1:value1|param2:value2|param3:value3]
```

### Available Directives

| Directive | Purpose | Parameters | Trigger |
|-----------|---------|------------|---------|
| `title` | Lock project title | `title:X` | After user confirms title |
| `logline` | Lock logline | `logline:X` | After user confirms logline |
| `character` | Save character | `name:X\|role:Y\|description:Z\|flaw:W\|arc:A` | Via `/character` command |
| `note` | Save idea/fragment | `idea:X` | Automatically during conversation |
| `beat` | Add outline beat | `beat:X` | Via `/beat` command |
| `scene` | Add scene to beat sheet | `number:N\|title:X\|description:Y` | Via `/scene` command |

### Emission Rules

1. **Proactive Pattern (Locking)**
   - Syd asks: "Should I lock this title?"
   - User confirms: "Yes" / "Lock it"
   - Syd emits: `[DIRECTIVE:title|title:Room for One]`

2. **Reactive Pattern (Commands)**
   - User types: `/character Emma`
   - Syd emits: `[DIRECTIVE:character|name:Emma|role:protagonist|...]`

3. **Auto-Track Pattern (Notes)**
   - During conversation, good ideas get saved automatically
   - Syd emits: `[DIRECTIVE:note|idea:Breakfast scene as inciting incident]`

### Example Response with Directive
```
That's a great title - "Room for One" captures the premise perfectly.

[DIRECTIVE:title|title:Room for One]

✓ Title locked: **Room for One**

Now let's nail the logline. Who's the protagonist?
```

---

## Commands (User-Initiated)

Commands let users manually trigger the same actions Syd can do automatically.

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/character [name]` | Add character to tracking | `/character Emma` |
| `/beat [text]` | Add outline beat | `/beat Act 1: They meet at a wedding` |
| `/scene [num] [title]` | Add scene to beat sheet | `/scene 1 Wedding Disaster` |
| `/note [idea]` | Save idea to notebook | `/note Rain scene at the end` |

### How Commands Work

1. User types command in chat
2. Syd recognizes the `/` prefix
3. Syd responds with confirmation + emits appropriate directive
4. State updates, UI reflects change

### Command Response Pattern
```
User: /character Lars
Syd: "Adding Lars to our cast.

[DIRECTIVE:character|name:Lars|role:love_interest|description:The guy both roommates want]

✓ Lars added as love interest."
```

---

## State Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                           PHASES                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 1: Foundation                                             │
│  ├── Lock Title        [DIRECTIVE:title|...]                     │
│  └── Lock Logline      [DIRECTIVE:logline|...]                   │
│                                                                  │
│  PHASE 2: Build-Out (happens in tandem)                          │
│  ├── Characters        [DIRECTIVE:character|...] via /character  │
│  ├── Outline (5-8)     [DIRECTIVE:beat|...] via /beat            │
│  ├── Beat Sheet (30)   [DIRECTIVE:scene|...] via /scene          │
│  └── Notebook          [DIRECTIVE:note|...] auto-tracked         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase Transitions

- **explore** → **build_out**: When title AND logline are locked
- **build_out** → **complete**: When characters, outline, and beats are populated

---

## Frontend Processing

The web interface (`ideate_web.py`) handles directives:

1. **Streaming**: Response streams to user in real-time (including directives)
2. **Stripping**: `stripDirectives()` removes directive syntax before display
3. **State Update**: Backend extracts and executes directives, sends state to frontend
4. **UI Update**: Sidebar reflects current state (title, logline, characters, etc.)

```javascript
// Frontend strips directives from display
function stripDirectives(text) {
    return text.replace(/\[DIRECTIVE:[^\]]+\]\s*/g, '');
}
```

---

## Backend Processing

The `IdeateSession` class in `ideate.py` handles:

1. **Extraction**: `_extract_directives()` parses `[DIRECTIVE:...]` from response
2. **Execution**: `_execute_directive()` updates session state
3. **State Management**: `get_state()` returns current fields, locked/populated status

```python
def _extract_directives(self, text: str) -> List[Dict]:
    pattern = r'\[DIRECTIVE:(\w+)\|([^\]]+)\]'
    # Returns: [{"action": "title", "params": {"title": "Room for One"}}, ...]
```

---

## RAG Buckets (Expert Knowledge)

Syd has access to three knowledge buckets via LightRAG:

| Bucket | Purpose | Query Examples |
|--------|---------|----------------|
| `scripts` | Film references, tone, execution | "romantic comedy films with roommate rivalry" |
| `books` | Structure, beats, craft | "protagonist character arc romantic comedy" |
| `plays` | Patterns, dynamics, archetypes | "enemies to lovers relationship dynamics" |

Queries are shaped based on current phase and state, then results inform Syd's responses.

---

## File Reference

| File | Purpose |
|------|---------|
| `lizzy/ideate.py` | Core session logic, directive processing, RAG integration |
| `lizzy/ideate_web.py` | FastAPI server, HTML template, streaming chat |
| `lizzy/database.py` | SQLite storage for projects, characters, scenes |
| `lizzy/static/` | Static assets (logo image) |

---

## Summary

- **Directives** = AI automatically saves ideas as conversation flows
- **Commands** = User manually triggers the same save actions
- Both update the same session state
- Frontend strips directives so users see clean responses
- State persists to database when user clicks "Save Project"
