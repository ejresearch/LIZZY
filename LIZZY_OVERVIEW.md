# Lizzy: AI-Powered Screenplay Writing Web Application

## What It Is

Lizzy is a web application that helps writers create romantic comedy screenplays using artificial intelligence. Accessible through any web browser, it guides users through a three-step process—Setup, Brainstorm, and Write—transforming story concepts into professionally formatted screenplays ready for production.

## How It Works

The application runs on a **web server** (the central computer that handles requests) built with Python, a popular programming language. When you interact with Lizzy's website, your browser sends requests to this server, which processes them and sends back responses—like generating scene ideas or formatting screenplay text.

**The AI Brain:**
Lizzy uses two types of artificial intelligence:
- **Knowledge Graphs**: Think of these as specialized libraries organized by a brilliant librarian. Lizzy has three: one filled with screenplay structure books, one with classic dramatic plays, and one with 90 modern romantic comedies. When you need ideas, the AI searches these libraries and finds relevant insights.
- **GPT-4o**: OpenAI's language model that writes the actual screenplay scenes. It's been instructed to write in a "Golden-Era Romcom" style—think Nora Ephron films like *When Harry Met Sally* or Nancy Meyers films like *The Holiday*.

Each project stores its information in a **database**—essentially a digital filing cabinet where all your characters, scenes, and drafts are organized and saved. Every screenplay gets its own separate database file, making it easy to back up or share your work.

## The User Experience

### Landing Page
When you first open Lizzy, you see a dashboard showing your projects and the three-step workflow. Click the "+" button to create a new screenplay or select an existing one to continue working.

### Setup Page (The Planning Room)
This is where you build your screenplay's foundation. It has six organized sections:

1. **Settings**: Name your project, set the genre, and write a one-sentence summary (called a "logline" in screenwriting). You can start from scratch or click "🎲 Generate Random" to let AI create an entire romantic comedy concept for you—complete with characters, scenes, and story themes.

2. **Characters**: Create your cast. Add names, assign roles (protagonist, love interest, supporting character, antagonist), and write descriptions. The AI uses these details when generating scenes.

3. **Scenes**: Manage your screenplay's 30-scene structure. This template follows a proven storytelling method used in Hollywood (based on "Save the Cat" story structure), divided into three acts. You can edit scene titles, descriptions, and assign which characters appear in each scene.

4. **Notes**: Document your creative vision—the story's deeper meaning (theme), the emotional feel you want (tone), similar films for reference, and personal inspiration.

5. **Brainstorm**: After generating ideas, review them here—all the creative suggestions from the AI experts.

6. **Screenplay**: The export hub where you download your finished screenplay in different formats: plain text, Microsoft Word, or PDF.

### Brainstorm Page (The Idea Generator)
This is where AI helps you develop each scene. When you click "Generate All Brainstorms," here's what happens behind the scenes:

For each of your 30 scenes, the system consults three AI experts:
- The **Books Expert** analyzes screenplay structure theory
- The **Plays Expert** references dramatic principles from classics like Shakespeare
- The **Scripts Expert** draws patterns from 90 modern romantic comedies

The AI combines these three perspectives into a detailed blueprint for each scene—suggesting character dynamics, emotional tone, key moments, and story beats. This takes about 1.5-2 minutes per scene.

You can watch the process in real-time through a progress window that shows which expert is being consulted, displays a running log of the AI's thinking, tracks elapsed time, and shows the estimated cost (typically a few cents per scene). You can generate all 30 scenes at once (45-60 minutes total), just the incomplete ones, or select specific scenes to brainstorm.

### Write Page (The Screenplay Generator)
Once you have brainstorms, this page converts them into actual screenplay format. The AI writes 700-900 word scenes in proper screenplay style—with scene headings, action descriptions, and dialogue.

Here's the clever part: when writing Scene 5, the AI reads the draft of Scene 4 to maintain continuity. This "feed-forward" approach means each scene naturally flows into the next without requiring the AI to remember the entire screenplay at once (which would be expensive and slow).

You can generate multiple versions of any scene to compare different approaches. Each draft is saved with version control, so you never lose earlier attempts. The progress window shows the AI's writing process, word count, and costs (typically a couple cents per scene).

### Export
Select which scenes to include (all 30, just Act 2, or a custom selection), choose which version of each scene you want, and download your screenplay. Lizzy formats everything professionally—proper scene headings, action lines, dialogue formatting—in whichever format you prefer: plain text, Microsoft Word document, or PDF.

## Key Features Explained

### Batch Processing
Instead of generating one scene at a time, you can automate the entire process. "Generate All" processes all 30 scenes automatically while you get coffee. Progress bars, live logs, and time estimates keep you informed.

### Version Control
Like "Save As" in Microsoft Word, but automatic. Every time you generate a scene, it's saved as a new version. Want to try a different approach? Generate a "New Version" without losing your previous work.

### Project Isolation
Each screenplay is completely self-contained in its own database file. This means you can easily back up projects, share them with collaborators, or work on multiple screenplays without them interfering with each other.

### AI-Generated Projects
The "Generate Random" feature creates an entire romantic comedy from scratch—unique characters with personalities, 30 detailed scene descriptions, thematic notes, and story inspiration. It's perfect for creative jumpstarts or overcoming writer's block.

### Cost Transparency
Before generating anything, Lizzy shows you exactly how much it will cost (using OpenAI's paid API). A complete 30-scene screenplay typically costs around $0.60—brainstorming all scenes runs about $0.15, writing all scenes about $0.45.

## Why It's Built This Way

### Three Expert System
Consulting three different knowledge sources prevents the AI from just copying one film. By combining screenplay theory (structure), classic drama (timeless principles), and modern romcoms (contemporary execution), the output balances educational grounding with fresh creativity.

### Feed-Forward Storytelling
Instead of trying to keep the entire screenplay in memory, the AI reads only the previous scene when writing the next one. This keeps costs down, speeds up generation, and maintains narrative flow naturally—just like a reader experiencing the story scene by scene.

### Browser-Based Design
Everything works through a website—no software to install, no command-line interfaces to learn. Real-time progress windows with visual feedback make the AI's process transparent instead of mysterious.

### Structured Templates
The 30-scene beat sheet provides a proven framework based on successful Hollywood films. It's fully customizable, but gives you a solid starting point so you're not facing a blank page.

### Multiple Export Formats
Plain text for simplicity, Microsoft Word for editing, PDF for sharing—whatever your workflow needs. The system handles all the screenplay formatting rules automatically (proper spacing, capitalization, margins).

## The Bottom Line

Lizzy is a complete screenplay writing tool that makes artificial intelligence accessible for creative writers. It transforms the intimidating process of writing a screenplay into a guided, transparent workflow with professional results. Whether you're an experienced screenwriter looking to accelerate your process or a beginner who wants structure and AI assistance, Lizzy provides the tools—all through an intuitive web interface that shows you exactly what's happening at every step.

The result: a professionally formatted romantic comedy screenplay, generated collaboratively between human creativity (your characters, story, and choices) and AI assistance (structure knowledge, scene ideas, and prose generation), ready to share, pitch, or produce.
