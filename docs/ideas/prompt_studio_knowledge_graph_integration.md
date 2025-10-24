# Prompt Studio + Knowledge Graph Integration

## The Idea

Integrate the interactive brainstorm functionality (querying expert knowledge graphs) into the Prompt Studio, creating a unified creative workspace with export capabilities.

## Current State

**Separate systems:**
- Prompt Studio: AI chat interface for general creative work
- Interactive Brainstorm: Queries 3 expert knowledge graphs (books, plays, scripts) but has broken chat UI

## Proposed Integration

### Core Concept
Make Prompt Studio the central creative workspace where writers can:

1. **Chat with expert knowledge graphs** (books, plays, scripts)
2. **See all expert responses** in a clean, organized UI
3. **Export insights directly** to project elements:
   - Save to scene brainstorms
   - Add to character notes
   - Update writer notes
   - Create new scenes
   - Add to general project notes

### Benefits

✅ **Consolidation** - One powerful chat interface instead of multiple scattered UIs
✅ **Better UX** - Leverage existing Prompt Studio infrastructure that already works
✅ **Visibility** - Make knowledge graph queries more visible and useful
✅ **Clean export workflow** - Direct integration with project database
✅ **Avoid complexity** - No need to fix broken chat mode in brainstorm page
✅ **Professional** - Single source of truth for creative exploration

### User Flow

```
1. Open Prompt Studio
2. Select mode: "AI Chat" or "Expert Knowledge Graphs"
3. In Expert mode:
   - Ask question about screenplay
   - See responses from all 3 buckets (books, plays, scripts)
   - Each response shown in expandable cards
4. Select insights you want to keep
5. Click "Export" and choose destination:
   - Scene brainstorm (select scene #)
   - Character note (select character)
   - Writer notes
   - New scene
6. Insight saved to project database
7. Continue conversation or start new query
```

### Technical Implementation

**Backend:**
- Reuse existing `InteractiveBrainstorm` class from `lizzy/interactive_brainstorm.py`
- Add new endpoints to Prompt Studio API for knowledge graph queries
- Create export endpoints to save insights to different project elements

**Frontend:**
- Add "Expert Knowledge Graphs" mode to Prompt Studio
- Display responses in cards (one per bucket)
- Add export UI with destination selector
- Show export success confirmation

**Database:**
- Store exported insights in appropriate tables
- Link exports back to original query for traceability
- Track which expert responses were used

### Features to Include

**Query capabilities:**
- Query all 3 buckets simultaneously
- Compare expert responses side-by-side
- Focus on specific scenes (scene-aware querying)
- Use Cohere reranking for better results

**Export options:**
- Export to scene brainstorm (append or replace)
- Export to character notes
- Export to writer notes
- Create new scene from insights
- Copy to clipboard

**History & tracking:**
- Show query history
- Mark which queries were exported
- Allow re-export of previous queries
- Search through past queries

### UI Design Notes

Use the existing Prompt Studio design system:
- Cream background (#f5f1e8)
- Red theme (#b83e3e)
- Georgia serif font
- Rounded borders and cards

**Expert response cards:**
```
┌─────────────────────────────────────┐
│ 📚 Books Expert                     │
│ ─────────────────────────────────── │
│ Response content here...            │
│                                     │
│ [Export] [Copy]                     │
└─────────────────────────────────────┘
```

**Export modal:**
```
┌─────────────────────────────────────┐
│ Export Insights                     │
│ ─────────────────────────────────── │
│ ○ Scene Brainstorm [Select scene ▼]│
│ ○ Character Note   [Select char  ▼]│
│ ○ Writer Notes                      │
│ ○ New Scene                         │
│                                     │
│        [Cancel]  [Export]           │
└─────────────────────────────────────┘
```

### Future Enhancements

- **AI synthesis**: Use Claude to synthesize all 3 expert responses into one coherent insight
- **Smart export**: AI suggests which scene/character to export to based on content
- **Templates**: Pre-made query templates for common screenplay questions
- **Batch queries**: Queue multiple questions and process them all
- **Collaboration**: Share queries and responses with other writers
- **Analytics**: Track which experts/buckets are most useful

## Why This is Better Than Separate Chat Mode

1. **User doesn't have to choose** between AI chat and expert graphs - it's all in one place
2. **Existing working infrastructure** - Prompt Studio already has chat UI that works
3. **Export is first-class** - not an afterthought, but core to the workflow
4. **Cleaner codebase** - remove broken chat mode, use one system
5. **Better discoverability** - writers will actually find and use knowledge graphs

## Implementation Priority

**Phase 1 (MVP):**
- Add "Expert Mode" toggle to Prompt Studio
- Query all 3 buckets and display results
- Basic export to scene brainstorm only

**Phase 2:**
- Export to all destinations (characters, notes, etc.)
- Query history
- Scene-focused queries

**Phase 3:**
- AI synthesis of expert responses
- Smart export suggestions
- Query templates

## Archived Reference

The original chat mode UI is saved in `docs/archived_ux/` for reference when building the Prompt Studio integration.

## Status

**Current:** Idea documented
**Next:** Design mockups for Expert Mode in Prompt Studio
**Owner:** TBD
**Priority:** Medium-High (improves core creative workflow)

---

*Documented: 2025-10-24*
*Updated: 2025-10-24*
