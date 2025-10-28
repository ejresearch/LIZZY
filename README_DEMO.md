# Lizzy Demo

Welcome to the Lizzy Demo! This is a streamlined version of Lizzy showcasing the visible frontend features and their backend capabilities.

## What's Included

This demo includes:

### Frontend Features
- **Landing Page**: Project management and navigation
- **Setup/Manager**: Create projects, edit characters, scenes, and story details
- **Brainstorm**: Interactive brainstorming with AI experts from books, plays, and scripts
- **Write**: Screenplay generation with professional formatting
- **Batch Processing**: Generate multiple scenes at once with live progress tracking

### Backend Capabilities
- FastAPI server with RESTful API
- SQLite database for project storage
- AI-powered brainstorming using RAG (Retrieval-Augmented Generation)
- Knowledge graphs from:
  - Best screenwriting books
  - Shakespeare's plays
  - 90 curated romantic comedies
- Screenplay formatting and generation

## Quick Start

### Prerequisites

1. Python 3.8 or higher
2. OpenAI API key
3. Required Python packages:
   ```bash
   pip install fastapi uvicorn python-dotenv anthropic openai lightrag nano-vectordb
   ```

### Setup

1. Configure your API keys:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

2. Launch the demo:
   ```bash
   ./launch_demo.sh
   ```

3. Open your browser to:
   ```
   http://localhost:8003
   ```

## Usage

1. **Create a Project**: Click the "+" button on the landing page
2. **Setup Your Story**: Go to Manager to add characters and scenes
3. **Brainstorm**: Use AI experts to develop your ideas
4. **Write**: Generate screenplay drafts

## Features

### Interactive Brainstorming
- Chat with three AI experts (Books, Plays, Scripts)
- Get insights enriched by knowledge graphs
- Focus on specific scenes or general story development

### Batch Processing
- Generate multiple brainstorms or scenes at once
- Live progress tracking with detailed logs
- Process selected scenes or all remaining scenes

### Professional Formatting
- Industry-standard screenplay format
- Scene headings, action lines, dialogue
- Character introductions and formatting

## Support

For questions or feedback, contact: ellejansickresearch@gmail.com

## Note

This is a demo version showcasing Lizzy's core capabilities. The full version includes additional features for advanced screenplay development.

---

**Powered by**: OpenAI GPT-4, LightRAG, Knowledge Graphs
