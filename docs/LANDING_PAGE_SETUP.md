# Lizzy 2.0 Landing Page - Setup Complete

## ✅ What's Been Built

### 1. Landing Page (`landing_page.html`)
Beautiful visual interface showing your 5-step pipeline:
- **Step 1: Start** - Create project
- **Step 2: Intake** - Add story data
- **Step 3: Brainstorm** - Generate blueprints
- **Step 4: Write** - Create prose
- **Step 5: Export** - Compile screenplay

**Features:**
- Clean, modern design with gradient background
- Interactive step cards with hover effects
- Progress tracking (marks completed steps with ✓)
- Stats display (time, cost, output)
- Responsive design for mobile/tablet
- LocalStorage to remember progress

### 2. Backend API (`landing_server.py`)
FastAPI server with endpoints:
- `GET /` - Serves landing page
- `GET /api/projects` - Lists all projects
- `GET /api/status/{project}` - Gets completion status
- `POST /api/launch` - Returns CLI command for module
- `GET /api/health` - Health check

**Smart Status Detection:**
- Checks if START complete (DB exists)
- Checks if INTAKE complete (has characters/scenes)
- Checks if BRAINSTORM complete (has sessions)
- Checks if WRITE complete (has drafts)
- Checks if EXPORT complete (has files)

### 3. Launch Script (`start_landing.sh`)
Easy startup:
```bash
./start_landing.sh
```

---

## 🚀 How to Use

### Start the Landing Page

```bash
./start_landing.sh
```

Then open your browser to: **http://localhost:8002**

### What You'll See

A beautiful landing page with 5 interactive steps. Click any step to get the CLI command to run.

### Current Behavior

For now, clicking a step shows an alert with the CLI command to run in your terminal:

```
python3 -m lizzy.start
python3 -m lizzy.intake
python3 -m lizzy.automated_brainstorm
python3 -m lizzy.automated_write
python3 -m lizzy.export
```

---

## 🔮 Future Enhancements (Easy to Add)

### Phase 1: Web Interfaces for Each Module

Instead of showing CLI commands, create web UIs:

#### START Module Web UI
```html
Simple form:
- Project name input
- Click "Create" → API creates project
- Shows success message
```

#### INTAKE Module Web UI
```html
Multi-step form:
- Step 1: Add characters (name, role, arc)
- Step 2: Edit 30 scenes (title, description)
- Step 3: Add writer notes (logline, theme, etc.)
- Save to database
```

#### BRAINSTORM Module Web UI
```html
Progress interface:
- Select scenes to brainstorm
- Show progress bar
- Display real-time status
- Show cost estimate
```

#### WRITE Module Web UI
```html
Editor interface:
- Scene selector
- Blueprint preview
- "Generate Draft" button
- Show prose output
- Edit/revise controls
```

#### EXPORT Module Web UI
```html
Export wizard:
- Version selector
- Format checkboxes
- "Export" button
- Download links
```

### Phase 2: Progress Tracking

Update landing page to show real-time progress:
- Query `/api/status/{project}` on load
- Mark completed steps with ✓
- Show stats (scenes written, drafts created, etc.)
- Enable/disable steps based on dependencies

### Phase 3: Project Switcher

Add dropdown to switch between projects:
```html
<select id="project-selector">
  <option>the_proposal_2_0</option>
  <option>bookshop_romance</option>
  <option>+ New Project</option>
</select>
```

---

## 📁 File Structure

```
LIZZY_ROMCOM/
├── landing_page.html          # Frontend (standalone HTML)
├── landing_server.py          # Backend API (FastAPI)
├── start_landing.sh           # Launch script
│
├── lizzy/
│   ├── start.py              # Module 1
│   ├── intake.py             # Module 2
│   ├── automated_brainstorm.py  # Module 3
│   ├── automated_write.py    # Module 4
│   ├── export.py             # Module 5
│   └── ...
│
└── projects/
    └── {project_name}/
        ├── {project_name}.db
        └── exports/
```

---

## 🎯 Current Ports

- **Port 8001:** Prompt Studio
- **Port 8002:** Landing Page (new!)

---

## 🛠️ API Examples

### Get All Projects

```bash
curl http://localhost:8002/api/projects
```

Response:
```json
{
  "projects": [
    {
      "name": "the_proposal_2_0",
      "path": "projects/the_proposal_2_0",
      "has_database": true
    }
  ]
}
```

### Get Project Status

```bash
curl http://localhost:8002/api/status/the_proposal_2_0
```

Response:
```json
{
  "current_project": "the_proposal_2_0",
  "steps": {
    "start": true,
    "intake": true,
    "brainstorm": false,
    "write": false,
    "export": false
  }
}
```

### Launch Module

```bash
curl -X POST http://localhost:8002/api/launch \
  -H "Content-Type: application/json" \
  -d '{"module": "start", "project_name": null}'
```

Response:
```json
{
  "module": "start",
  "command": "python3 -m lizzy.start",
  "message": "Run this command in your terminal:\n\npython3 -m lizzy.start"
}
```

---

## 💡 Next Steps

### Option A: Keep CLI-First Approach
Current setup works great - landing page is a visual guide that tells users which CLI commands to run.

**Pros:**
- Simple
- No complex frontend needed
- Works immediately

**Cons:**
- User must switch to terminal
- Less "polished" feeling

### Option B: Build Web UIs
Create actual web interfaces for each module.

**Pros:**
- Professional, all-in-browser experience
- Better for non-technical users
- More impressive demo

**Cons:**
- More development time
- Need to build forms, validation, etc.
- Duplicate logic (CLI + Web)

### Option C: Hybrid Approach
Keep CLI as primary, add web UIs for key modules only:
- **START:** Web form (simple)
- **INTAKE:** Web form (complex but worth it)
- **BRAINSTORM:** CLI (already fast)
- **WRITE:** CLI (already fast)
- **EXPORT:** Web download button (simple)

**Recommended:** Option C gives best ROI

---

## 🎨 Design Principles

The landing page follows these principles:

1. **Visual Pipeline:** Users see the entire workflow at a glance
2. **Progress Tracking:** Completed steps are marked with ✓
3. **Clear Stats:** Time, cost, and output expectations upfront
4. **Easy Navigation:** One click to launch any module
5. **Responsive:** Works on desktop, tablet, mobile

---

## 🚧 Known Limitations

1. **CLI Commands Only:** Currently shows terminal commands instead of launching modules
2. **No Real-Time Updates:** Must refresh to see status changes
3. **Single Project:** Doesn't show project selector yet
4. **No Auth:** Anyone on localhost can access
5. **No Persistence:** Progress tracking uses localStorage (browser-only)

All easily fixable with future iterations!

---

## ✅ What Works Right Now

1. **Landing page loads** at http://localhost:8002
2. **Beautiful UI** with 5-step visualization
3. **Click any step** → get CLI command to run
4. **API endpoints** work and return project status
5. **Health check** confirms server is running

---

## 🎬 Demo Flow

1. Open browser to `http://localhost:8002`
2. See beautiful landing page with 5 steps
3. Click "Create Project" (Step 1)
4. Get CLI command: `python3 -m lizzy.start`
5. Run command in terminal
6. Refresh landing page
7. Step 1 shows ✓ (completed)
8. Click "Add Story Data" (Step 2)
9. And so on...

---

**Ready to launch! Run: `./start_landing.sh`**
