# LIZZY Current Architecture (Legacy)

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: IDEATE                                      │
│                        (ideate_web.py)                                       │
│                         Port 8888                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │   User ◄──────► Syd (GPT-4.1-mini)                                    │  │
│  │                      │                                                 │  │
│  │                      │ embeds [DIRECTIVE:action|params]               │  │
│  │                      ▼                                                 │  │
│  │              ┌───────────────┐                                        │  │
│  │              │ Regex Parser  │◄─── Fallback: natural language parse   │  │
│  │              └───────┬───────┘                                        │  │
│  │                      │                                                 │  │
│  │                      ▼                                                 │  │
│  │              ┌───────────────┐      ┌─────────────────────┐           │  │
│  │              │ State Manager │ ───► │ ideate_sessions.db  │           │  │
│  │              └───────────────┘      │  - title, logline   │           │  │
│  │                                     │  - characters[]     │           │  │
│  │   Slash commands:                   │  - scenes[]         │           │  │
│  │   /character, /scene, /beat,        │  - notebook[]       │           │  │
│  │   /note, /lock                      │  - messages[]       │           │  │
│  │                                     └─────────────────────┘           │  │
│  │                                                                        │  │
│  │   Optional: RAG queries during conversation                           │  │
│  │   (books/plays/scripts buckets)                                       │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                         "Create Project" button                              │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROJECT CREATION                                      │
│                      (project_creator.py)                                    │
│                                                                              │
│   ideate_sessions.db ──────────────────────► projects/{name}/{name}.db      │
│                                                                              │
│   Copies: title, logline, characters, scenes, notes                         │
│   Creates: project directory + exports/ subfolder                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ USER EXITS WEB UI
                                     │ RUNS CLI COMMAND
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PHASE 2: BRAINSTORM                                    │
│                    (automated_brainstorm.py)                                 │
│                           CLI only                                           │
│                                                                              │
│   For each of 30 scenes:                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│   │  │   BOOKS     │  │   PLAYS     │  │   SCRIPTS   │                  │   │
│   │  │   bucket    │  │   bucket    │  │   bucket    │                  │   │
│   │  │  (216 MB)   │  │  (200 MB)   │  │  (271 MB)   │                  │   │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                  │   │
│   │         │                │                │                          │   │
│   │         └────────────────┼────────────────┘                          │   │
│   │                          │ asyncio.gather (PARALLEL)                 │   │
│   │                          ▼                                           │   │
│   │                  ┌───────────────┐                                   │   │
│   │                  │  LightRAG     │                                   │   │
│   │                  │  aquery()     │                                   │   │
│   │                  │  mode=hybrid  │                                   │   │
│   │                  └───────┬───────┘                                   │   │
│   │                          │                                           │   │
│   │                          ▼                                           │   │
│   │                  ┌───────────────┐                                   │   │
│   │                  │   Cohere      │  (optional reranking)             │   │
│   │                  │   Rerank      │                                   │   │
│   │                  └───────┬───────┘                                   │   │
│   │                          │                                           │   │
│   │                          ▼                                           │   │
│   │                  ┌───────────────┐                                   │   │
│   │                  │  GPT-4o       │                                   │   │
│   │                  │  Synthesis    │                                   │   │
│   │                  └───────┬───────┘                                   │   │
│   │                          │                                           │   │
│   │                          ▼                                           │   │
│   │                  ┌───────────────────────────┐                       │   │
│   │                  │  brainstorm_sessions      │                       │   │
│   │                  │  table in project.db      │                       │   │
│   │                  │  - scene_id               │                       │   │
│   │                  │  - bucket_used            │                       │   │
│   │                  │  - content (blueprint)    │                       │   │
│   │                  └───────────────────────────┘                       │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Also generates: delta summaries (compressed context for next scene)       │
│   Cost: ~$0.15 for 30 scenes                                                │
│   Time: ~2-3 minutes                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ USER RUNS ANOTHER CLI COMMAND
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 3: WRITE                                       │
│                      (automated_write.py)                                    │
│                           CLI only                                           │
│                                                                              │
│   For each of 30 scenes:                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │   ┌─────────────────────┐   ┌─────────────────────┐                 │   │
│   │   │ Scene description   │ + │ Brainstorm blueprint │                │   │
│   │   │ (from scenes table) │   │ (from brainstorm_    │                │   │
│   │   └─────────────────────┘   │  sessions table)     │                │   │
│   │                             └─────────────────────┘                 │   │
│   │                  │                    │                              │   │
│   │                  └────────┬───────────┘                              │   │
│   │                           │                                          │   │
│   │                           ▼                                          │   │
│   │   ┌─────────────────────────────────────────────────────────┐       │   │
│   │   │  Previous scene draft (feed-forward continuity)         │       │   │
│   │   └─────────────────────────────────────────────────────────┘       │   │
│   │                           │                                          │   │
│   │                           ▼                                          │   │
│   │                   ┌───────────────┐                                  │   │
│   │                   │    GPT-4o     │                                  │   │
│   │                   │  (streaming)  │                                  │   │
│   │                   └───────┬───────┘                                  │   │
│   │                           │                                          │   │
│   │                           ▼                                          │   │
│   │                   700-900 word prose                                 │   │
│   │                   screenplay scene                                   │   │
│   │                           │                                          │   │
│   │                           ▼                                          │   │
│   │                  ┌───────────────────────────┐                       │   │
│   │                  │  scene_drafts table       │                       │   │
│   │                  │  - scene_id               │                       │   │
│   │                  │  - content                │                       │   │
│   │                  │  - version                │                       │   │
│   │                  │  - word_count             │                       │   │
│   │                  │  - tokens_used            │                       │   │
│   │                  │  - cost_estimate          │                       │   │
│   │                  └───────────────────────────┘                       │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Style: Golden-era romcom (When Harry Met Sally, You've Got Mail)          │
│   Cost: ~$0.45 for 30 scenes                                                │
│   Time: ~10-15 minutes                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ USER RUNS ANOTHER CLI COMMAND
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 4: EXPORT                                      │
│                          (export.py)                                         │
│                           CLI only                                           │
│                                                                              │
│   scene_drafts ──────────────────────────► Compiled Screenplay              │
│                                                                              │
│   Output formats:                                                           │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│   │    .txt     │ │    .md      │ │  .fountain  │ │    .fdx     │          │
│   │  (plain)    │ │ (markdown)  │ │ (industry   │ │(Final Draft)│          │
│   │             │ │             │ │  standard)  │ │             │          │
│   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                                              │
│   Saved to: projects/{name}/exports/                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


## Data Flow Summary

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  ideate_sessions │     │   project.db     │     │     exports/     │
│       .db        │────►│                  │────►│                  │
│                  │     │  - characters    │     │  - script.fountain│
│  - messages      │     │  - scenes        │     │  - script.fdx    │
│  - characters    │     │  - brainstorm_   │     │                  │
│  - scenes        │     │    sessions      │     │                  │
│  - notebook      │     │  - scene_drafts  │     │                  │
│  - title/logline │     │  - writer_notes  │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                         │
        │    IDEATE              │    BRAINSTORM + WRITE + EXPORT
        │                         │
```


## RAG Buckets (Shared Knowledge)

```
rag_buckets/
├── books/     (216 MB)  ── Screenwriting craft books
│                           Structure, beats, pacing
│
├── plays/     (200 MB)  ── Complete Shakespeare
│                           Dialogue, dramatic patterns
│
└── scripts/   (271 MB)  ── Selected romcom screenplays
                            Visual storytelling, execution
```


## Current Pain Points

```
   IDEATE                          BRAINSTORM                    WRITE
      │                                │                           │
      ▼                                ▼                           ▼
┌───────────┐                   ┌───────────┐               ┌───────────┐
│ Web UI    │    EXIT &         │ CLI only  │    EXIT &     │ CLI only  │
│ Port 8888 │ ──────────────►   │           │ ──────────►   │           │
└───────────┘  RUN COMMAND      └───────────┘  RUN COMMAND  └───────────┘
      │                                │                           │
      ▼                                ▼                           ▼
  Directive                       No chat,                    No chat,
  parsing is                      just batch                  just batch
  fragile                         processing                  processing


PROBLEMS:
1. User exits/re-enters between phases (broken flow)
2. Syd only exists in IDEATE (experts not conversational)
3. Directive regex parsing is unreliable
4. No unified conversation history across phases
5. Brainstorm/write are batch-only, not interactive chat
```


## Models Used

| Phase | Model | Purpose |
|-------|-------|---------|
| IDEATE | GPT-4.1-mini | Syd conversation |
| IDEATE (RAG) | LightRAG default | Bucket queries |
| BRAINSTORM (RAG) | GPT-5.1 | LightRAG queries |
| BRAINSTORM (synthesis) | GPT-5 | Combine expert insights |
| WRITE | GPT-4o | Prose generation |
| Delta summaries | GPT-5.1 | Compress for context |

Note: Some model names in code (GPT-5, GPT-5.1) appear to be placeholders/typos
