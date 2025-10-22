# Complete Function List - Brainstorm Modules

## Interactive Brainstorm (`lizzy/interactive_brainstorm.py`)

### Core Initialization & Context
1. `__init__(db_path: Path)` - Initialize Interactive Brainstorm with database path
2. `_discover_buckets() -> List[str]` - Find all available RAG buckets in rag_buckets/
3. `load_project_context() -> None` - Load project, characters, scenes, writer notes from database

### Context Building
4. `build_context_summary() -> str` - Create formatted project context summary
5. `get_character_context(character_name: str) -> Optional[Dict]` - Get specific character data
6. `get_scene_context(scene_number: int) -> Optional[Dict]` - Get specific scene data

### 🆕 Scene-Specific Mode (Improvement #1)
7. `enter_scene_focus_mode(scene_number: int) -> bool` - Lock conversation to Scene N
8. `exit_scene_focus_mode() -> None` - Return to project-wide queries
9. `_get_scene_blueprint(scene_number: int) -> Optional[str]` - Retrieve scene blueprint from database
10. `show_focused_scene_blueprint() -> None` - Display focused scene's blueprint

### 🆕 Bucket Comparison (Improvement #2)
11. `query_buckets_comparison(query: str, buckets: List[str]) -> Dict` *(async)* - Query all buckets without synthesis
12. `display_comparison(comparison: Dict) -> None` - Show side-by-side expert responses

### 🆕 Export to Blueprint (Improvement #3)
13. `export_conversation_to_blueprint(scene_number: int) -> Optional[str]` *(async)* - Convert conversation to structured blueprint
14. `save_as_blueprint(scene_number: int, blueprint: str) -> bool` - Save blueprint to database

### 🆕 Query History (Improvement #4)
15. `_show_query_history() -> None` - Display last 10 queries with timestamps

### 🆕 Suggested Questions (Improvement #5)
16. `generate_follow_up_questions(query: str, response: str) -> List[str]` *(async)* - Generate 3 AI follow-up suggestions

### RAG Query System
17. `query_buckets(query: str, buckets: List[str], mode: str, use_reranking: bool) -> List[Dict]` *(async)* - Query multiple LightRAG buckets
18. `enhance_query_with_context(user_query: str, context_elements: Optional[Dict]) -> str` - Add project/scene context to queries
19. `display_results(results: List[Dict]) -> None` - Display query results in panels

### Conversation Management
20. `run_conversation_mode() -> None` *(async)* - Run continuous conversation loop
21. `_log_conversation_turn(role: str, content: str) -> None` - Log conversation to file
22. `_init_conversation_log(buckets: List[str]) -> None` - Initialize conversation log with metadata
23. `_build_conversation_context() -> str` - Build recent conversation history (last 6 messages)
24. `_conversational_synthesis(user_input: str, rag_results: List[Dict]) -> str` *(async)* - Use GPT-4o to synthesize RAG results
25. `_save_conversation() -> None` - Save conversation to writer_notes.braindump

### Main Execution
26. `run_interactive_session() -> None` *(async)* - Main interactive session loop
27. `main()` *(async, module-level)* - CLI entrypoint with project selection

---

## Automated Brainstorm (`lizzy/automated_brainstorm.py`)

### Core Initialization & Context
1. `__init__(db_path: Path)` - Initialize Automated Brainstorm with database path
2. `load_project_context() -> None` - Load all project data from database
3. `build_story_outline() -> str` - Format complete story outline for experts

### Scene Context & Feed-Forward
4. `get_surrounding_context(scene: Dict) -> Dict[str, Optional[str]]` - Get previous/next scene context
5. `_get_scene_blueprint(scene_id: int) -> Optional[str]` - Retrieve synthesized blueprint for scene
6. `_generate_delta_summary(scene: Dict, blueprint: str) -> str` *(async)* - Compress blueprint to 250-token delta
7. `_get_scene_delta_summary(scene: Dict) -> Optional[str]` - Get or generate delta summary

### 🆕 Confidence Scores (Improvement #16)
8. `calculate_expert_agreement(bucket_results: List[Dict]) -> Dict[str, float]` - Calculate confidence scores (0-1) per section
9. `display_confidence_scores(scene_num: int, scores: Dict[str, float]) -> None` - Show color-coded confidence indicators

### 🆕 Preview Mode (Improvement #17)
10. `preview_scene_prompts(scene_number: int) -> None` - Show prompts without executing (with token estimates)

### 🆕 Budget Estimator (Improvement #18)
11. `estimate_cost_and_time(num_scenes: int, start_from: int) -> Dict` - Calculate cost/time before processing
12. `display_cost_estimate(estimate: Dict) -> None` - Display formatted cost breakdown

### 🆕 Selective Regeneration (Improvement #15)
13. `regenerate_scenes(scene_numbers: List[int]) -> None` *(async)* - Regenerate specific scenes only

### Expert Query System
14. `build_expert_query(scene: Dict, bucket_name: str) -> str` - Build bucket-specific expert prompt
15. `query_bucket_for_scene(scene: Dict, bucket_name: str) -> Optional[Dict]` *(async)* - Query single bucket with LightRAG
16. `synthesize_expert_insights(scene: Dict, bucket_results: List[Dict]) -> str` *(async)* - Synthesize 3 experts with GPT-4o

### Scene Processing
17. `process_scene(scene: Dict, progress: Progress, task_id) -> Dict` *(async)* - Process single scene through all buckets
18. `_save_brainstorm_session(scene: Dict, bucket_results: List[Dict], synthesized: str) -> None` - Save to database
19. `display_scene_result(result: Dict) -> None` - Display completed scene blueprint

### 🆕 Batch Processing with Resume (Improvement #14)
20. `run_batch_processing(start_from: int = 1) -> None` *(async)* - Main batch processing loop with resume support

### Main Execution
21. `main()` *(async, module-level)* - CLI entrypoint with mode selection (all/resume/regenerate)

---

## Function Count Summary

| Module | Total Functions | New (Improvements) | Async Functions |
|--------|----------------|-------------------|-----------------|
| **Interactive Brainstorm** | 27 | 6 new | 7 async |
| **Automated Brainstorm** | 21 | 5 new | 8 async |
| **TOTAL** | **48** | **11 new** | **15 async** |

---

## Function Categories

### Interactive Brainstorm by Category

**Setup & Context (6 functions)**
- `__init__`, `_discover_buckets`, `load_project_context`
- `build_context_summary`, `get_character_context`, `get_scene_context`

**Scene Focus Mode (4 functions)** 🆕
- `enter_scene_focus_mode`, `exit_scene_focus_mode`
- `_get_scene_blueprint`, `show_focused_scene_blueprint`

**Comparison & Export (4 functions)** 🆕
- `query_buckets_comparison`, `display_comparison`
- `export_conversation_to_blueprint`, `save_as_blueprint`

**History & Suggestions (2 functions)** 🆕
- `_show_query_history`, `generate_follow_up_questions`

**RAG Queries (3 functions)**
- `query_buckets`, `enhance_query_with_context`, `display_results`

**Conversation Loop (6 functions)**
- `run_conversation_mode`, `_log_conversation_turn`, `_init_conversation_log`
- `_build_conversation_context`, `_conversational_synthesis`, `_save_conversation`

**Main Execution (2 functions)**
- `run_interactive_session`, `main`

---

### Automated Brainstorm by Category

**Setup & Context (3 functions)**
- `__init__`, `load_project_context`, `build_story_outline`

**Feed-Forward System (4 functions)**
- `get_surrounding_context`, `_get_scene_blueprint`
- `_generate_delta_summary`, `_get_scene_delta_summary`

**Quality & Cost Tools (4 functions)** 🆕
- `calculate_expert_agreement`, `display_confidence_scores`
- `estimate_cost_and_time`, `display_cost_estimate`

**Preview & Regeneration (2 functions)** 🆕
- `preview_scene_prompts`, `regenerate_scenes`

**Expert System (3 functions)**
- `build_expert_query`, `query_bucket_for_scene`, `synthesize_expert_insights`

**Scene Processing (3 functions)**
- `process_scene`, `_save_brainstorm_session`, `display_scene_result`

**Batch Processing (2 functions)**
- `run_batch_processing` (with resume support 🆕), `main`

---

## Key Async Functions

### Interactive Brainstorm (7 async)
1. `query_buckets_comparison()` - Multi-bucket queries
2. `export_conversation_to_blueprint()` - GPT-4o conversion
3. `generate_follow_up_questions()` - GPT-4o-mini suggestions
4. `query_buckets()` - LightRAG queries with reranking
5. `run_conversation_mode()` - Conversation loop
6. `_conversational_synthesis()` - GPT-4o synthesis
7. `run_interactive_session()` - Main session
8. `main()` - CLI entrypoint

### Automated Brainstorm (8 async)
1. `_generate_delta_summary()` - GPT-4o-mini compression
2. `regenerate_scenes()` - Selective regeneration
3. `query_bucket_for_scene()` - Single bucket query
4. `synthesize_expert_insights()` - GPT-4o synthesis
5. `process_scene()` - Full scene processing
6. `run_batch_processing()` - Batch loop
7. `main()` - CLI entrypoint

---

## Function Dependencies

### Interactive Brainstorm Call Chain

```
main()
 └─> run_interactive_session()
      ├─> load_project_context()
      │    ├─> get_character_context()  [called by user]
      │    └─> get_scene_context()      [called by user]
      │
      └─> run_conversation_mode()
           ├─> enter_scene_focus_mode()
           │    └─> _get_scene_blueprint()
           │
           ├─> query_buckets_comparison()
           │    ├─> query_buckets()
           │    └─> display_comparison()
           │
           ├─> export_conversation_to_blueprint()
           │    └─> save_as_blueprint()
           │
           ├─> _show_query_history()
           │
           ├─> query_buckets()
           │    └─> enhance_query_with_context()
           │
           ├─> _conversational_synthesis()
           │
           ├─> generate_follow_up_questions()
           │
           └─> _save_conversation()
```

### Automated Brainstorm Call Chain

```
main()
 ├─> estimate_cost_and_time()
 │    └─> display_cost_estimate()
 │
 ├─> preview_scene_prompts()
 │    └─> build_expert_query()
 │
 ├─> run_batch_processing(start_from=N)
 │    └─> process_scene()
 │         ├─> get_surrounding_context()
 │         │    └─> _get_scene_delta_summary()
 │         │         └─> _generate_delta_summary()
 │         │
 │         ├─> query_bucket_for_scene()
 │         │    └─> build_expert_query()
 │         │
 │         ├─> synthesize_expert_insights()
 │         │
 │         ├─> calculate_expert_agreement()
 │         │
 │         ├─> _save_brainstorm_session()
 │         │
 │         └─> display_scene_result()
 │              └─> display_confidence_scores()
 │
 └─> regenerate_scenes([5,12,18])
      ├─> estimate_cost_and_time()
      └─> process_scene() [for each scene]
```

---

## New Functions Added in This Implementation

### Interactive Brainstorm (6 new)
1. ✨ `enter_scene_focus_mode()` - Scene focus
2. ✨ `exit_scene_focus_mode()` - Exit focus
3. ✨ `show_focused_scene_blueprint()` - Display blueprint
4. ✨ `query_buckets_comparison()` - Side-by-side comparison
5. ✨ `display_comparison()` - Format comparison display
6. ✨ `export_conversation_to_blueprint()` - Export to blueprint
7. ✨ `save_as_blueprint()` - Save blueprint
8. ✨ `_show_query_history()` - Query history display
9. ✨ `generate_follow_up_questions()` - AI suggestions

**Modified:**
- `enhance_query_with_context()` - Added scene focus injection
- `run_conversation_mode()` - Added 7 new commands

### Automated Brainstorm (5 new)
1. ✨ `calculate_expert_agreement()` - Confidence scoring
2. ✨ `display_confidence_scores()` - Show scores
3. ✨ `preview_scene_prompts()` - Preview mode
4. ✨ `estimate_cost_and_time()` - Cost estimation
5. ✨ `display_cost_estimate()` - Display estimate
6. ✨ `regenerate_scenes()` - Selective regeneration

**Modified:**
- `run_batch_processing()` - Added start_from parameter
- `process_scene()` - Added confidence scoring
- `display_scene_result()` - Added confidence display
- `main()` - Added 3-mode selection

---

## Public vs Private Functions

### Interactive Brainstorm
**Public (21):**
- All methods without leading underscore
- User-facing commands: focus, compare, export, history, etc.

**Private (6):**
- `_discover_buckets()`
- `_get_scene_blueprint()`
- `_show_query_history()`
- `_log_conversation_turn()`
- `_init_conversation_log()`
- `_build_conversation_context()`
- `_conversational_synthesis()`
- `_save_conversation()`

### Automated Brainstorm
**Public (15):**
- All methods without leading underscore
- Main processing functions

**Private (6):**
- `_get_scene_blueprint()`
- `_generate_delta_summary()`
- `_get_scene_delta_summary()`
- `_save_brainstorm_session()`

---

## Function Signatures Quick Reference

### Interactive Brainstorm
```python
# Scene Focus
enter_scene_focus_mode(scene_number: int) -> bool
exit_scene_focus_mode() -> None
show_focused_scene_blueprint() -> None

# Comparison
async query_buckets_comparison(query: str, buckets: List[str]) -> Dict
display_comparison(comparison: Dict) -> None

# Export
async export_conversation_to_blueprint(scene_number: int) -> Optional[str]
save_as_blueprint(scene_number: int, blueprint: str) -> bool

# Suggestions
async generate_follow_up_questions(query: str, response: str) -> List[str]
```

### Automated Brainstorm
```python
# Confidence
calculate_expert_agreement(bucket_results: List[Dict]) -> Dict[str, float]
display_confidence_scores(scene_num: int, scores: Dict[str, float]) -> None

# Cost/Preview
estimate_cost_and_time(num_scenes: int, start_from: int = 1) -> Dict
display_cost_estimate(estimate: Dict) -> None
preview_scene_prompts(scene_number: int) -> None

# Regeneration
async regenerate_scenes(scene_numbers: List[int]) -> None
async run_batch_processing(start_from: int = 1) -> None
```

---

## Lines of Code per Function Category

### Interactive Brainstorm (~823 lines total)
- Scene Focus Mode: ~80 lines
- Comparison & Export: ~120 lines
- History & Suggestions: ~40 lines
- RAG Query System: ~160 lines
- Conversation Loop: ~380 lines
- Setup & Main: ~40 lines

### Automated Brainstorm (~1,229 lines total)
- Feed-Forward System: ~180 lines
- Confidence & Cost Tools: ~200 lines
- Preview & Regeneration: ~140 lines
- Expert System: ~320 lines
- Scene Processing: ~240 lines
- Batch Processing & Main: ~150 lines
