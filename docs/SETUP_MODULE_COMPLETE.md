# Setup Module - Complete! ✓

## What's Been Built

### Combined "Setup" Module
Replaced START + INTAKE with a single unified **Setup** module that acts as a project manager.

---

## New Landing Page Flow (4 Steps)

```
1. Setup      → Project manager (settings, characters, scenes, notes)
2. Brainstorm → Blueprint generation
3. Write      → Prose generation
4. Export     → Compile screenplay
```

**From 5 steps to 4 steps** - cleaner, more intuitive!

---

## Setup Page Features

### Main View: Project List
```
┌─────────────────────────────────────────┐
│  Your Projects                          │
├─────────────────────────────────────────┤
│  My Romcom              [Open] [Delete] │
│  The Proposal 2.0       [Open] [Delete] │
│                                         │
│  [+ Create New Project]                 │
└─────────────────────────────────────────┘
```

### Project Editor: 4 Tabs

#### 1. Settings Tab
- Project name
- Genre (dropdown)
- Logline (textarea)
- Template selection:
  - ○ Blank Project
  - ● 30-Scene Beat Sheet

#### 2. Characters Tab
- List of characters (name, description, role)
- [Edit] [Delete] buttons per character
- [+ Add Character] button

#### 3. Scenes Tab
- List of all 30 scenes
- Scene number badge
- Scene title and description
- Filter by act (All / Act 1 / Act 2 / Act 3)
- [Edit] button per scene

#### 4. Notes Tab
- Theme
- Tone
- Comparable Films
- Inspiration / Additional Notes

---

## Design Aesthetic

Matches the landing page:
- **Warm beige background** (#f5f1e8)
- **Deep red accents** (#b83e3e)
- **Georgia serif font**
- **White rounded cards** with red borders
- **Pill-shaped buttons**
- **Elegant, editorial feel**

---

## API Endpoints Added

### GET /setup
Serves the setup page HTML

### GET /api/project/{project_name}
Returns full project data:
- name, genre, logline
- characters array
- scenes array
- notes object

### POST /api/project/save
Creates or updates a project:
- Creates new project with beat sheet or blank
- Updates existing project metadata

### DELETE /api/project/{project_name}
Deletes a project and all its data

---

## User Flow

### Creating New Project

1. Click "Setup" on landing page
2. See project list (or empty state)
3. Click "+ Create New Project"
4. Fill in:
   - Project Name: "My Romcom"
   - Logline: "A bookshop owner falls for..."
   - Template: 30-Scene Beat Sheet
5. Click "Save Project"
6. Success! Project created with:
   - 4 default characters
   - 30 pre-populated scenes
   - Empty notes

### Editing Existing Project

1. Click "Setup" on landing page
2. See list of projects
3. Click "Open" on a project
4. Switch between tabs:
   - **Settings** - Edit basic info
   - **Characters** - View/edit cast
   - **Scenes** - View/edit all 30 scenes
   - **Notes** - Add theme, tone, comps
5. Click "Save Project"
6. Changes saved to database

---

## What Works Right Now

✓ Landing page navigation (4 steps)
✓ Setup page loads at /setup
✓ Project list displays all projects
✓ Create new project (blank or beat sheet)
✓ Open existing project
✓ Delete project (with confirmation)
✓ Settings tab (view/edit)
✓ Characters tab (view only - edit coming soon)
✓ Scenes tab (view only - edit coming soon)
✓ Notes tab (view only - edit coming soon)
✓ Save project metadata
✓ Beautiful warm editorial design

---

## What's Next (Easy Additions)

### Character Editor Modal
When user clicks "Edit" on a character:
```
┌─────────────────────────────────┐
│  Edit Character                 │
├─────────────────────────────────┤
│  Name: [Protagonist        ]    │
│  Role: [protagonist ▼      ]    │
│  Description:                   │
│  [________________________]     │
│  Arc:                           │
│  [________________________]     │
│                                 │
│  [Save] [Cancel]                │
└─────────────────────────────────┘
```

### Scene Editor Modal
When user clicks "Edit" on a scene:
```
┌─────────────────────────────────┐
│  Edit Scene 5                   │
├─────────────────────────────────┤
│  Title: [Debate            ]    │
│  Description:                   │
│  [________________________]     │
│  Characters: [____________]     │
│  Tone: [_________________]      │
│                                 │
│  [Save] [Cancel]                │
└─────────────────────────────────┘
```

### Add Character Modal
```
┌─────────────────────────────────┐
│  New Character                  │
├─────────────────────────────────┤
│  Name: [__________________]     │
│  Role: [protagonist ▼     ]     │
│  Description:                   │
│  [________________________]     │
│  Arc:                           │
│  [________________________]     │
│                                 │
│  [Add] [Cancel]                 │
└─────────────────────────────────┘
```

---

## File Structure

```
LIZZY_ROMCOM/
├── landing_page.html          # 4-step landing page
├── setup_page.html            # Project manager (NEW!)
├── landing_server.py          # Backend with new endpoints
└── start_landing.sh           # Server launcher
```

---

## How to Use

### Start the Server

```bash
./start_landing.sh
```

Then open: **http://localhost:8002**

### Create a Project

1. Click "Setup" (step 1)
2. Click "+ Create New Project"
3. Enter name and logline
4. Choose "30-Scene Beat Sheet"
5. Click "Save Project"
6. Project created with full structure!

### Edit a Project

1. Click "Setup"
2. Click "Open" on your project
3. Switch between tabs to view/edit
4. Click "Save Project" when done

---

## Next Steps

**Priority 1:** Add character/scene editors
- Modal dialogs for editing
- Save to database
- Update UI on save

**Priority 2:** Build other module UIs
- Brainstorm page
- Write page
- Export page

**Priority 3:** Real-time status tracking
- Mark Setup as complete when project has data
- Enable/disable steps based on progress

---

## Current Status

**Landing Page:** ✓ Complete (4-step flow)
**Setup Page:** ✓ Core complete (view/create/delete)
**Setup API:** ✓ Complete (all CRUD operations)
**Character Editing:** ⚠️ View only (edit modal needed)
**Scene Editing:** ⚠️ View only (edit modal needed)
**Notes Editing:** ⚠️ View only (save functionality needed)

---

**Ready to test! Visit http://localhost:8002 and click "Setup"**
