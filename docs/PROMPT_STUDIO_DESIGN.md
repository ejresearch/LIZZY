# Prompt Studio Design for Lizzy 2.0

**Purpose:** Centralized prompt management, versioning, testing, and optimization system

---

## 🎯 Overview

**Prompt Studio** is a development tool for managing all LLM prompts in Lizzy 2.0. It provides:
- 🔧 **Prompt Templates** - Centralized, versioned prompt definitions
- 🧪 **Testing & Validation** - Dry-run prompts without API calls
- 📊 **Quality Metrics** - Automated response validation
- 📝 **Audit Trail** - Complete logging of all prompt executions
- 🎨 **Visual Editor** - Interactive prompt builder (future)
- 📈 **Analytics** - Track prompt performance over time

---

## 🏗️ Architecture

### Directory Structure
```
lizzy/prompt_studio/
├── __init__.py
│
├── context/                    # Context loading from database
│   ├── __init__.py
│   ├── types.py               # SceneContext, ProjectContext data classes
│   └── retrieval.py           # SQL queries to load context
│
├── templates/                  # Prompt templates
│   ├── __init__.py
│   ├── base.py                # Base template class
│   ├── brainstorm/            # Brainstorm templates
│   │   ├── __init__.py
│   │   ├── books.py           # Books bucket template
│   │   ├── plays.py           # Plays bucket template
│   │   ├── scripts.py         # Scripts bucket template
│   │   └── synthesis.py       # Synthesis template
│   └── write/                 # Write templates (future)
│       ├── __init__.py
│       ├── scene_draft.py     # Scene writing template
│       └── dialogue.py        # Dialogue polishing template
│
├── builders/                   # Prompt construction
│   ├── __init__.py
│   ├── base.py                # BasePromptBuilder
│   ├── brainstorm.py          # BrainstormPromptBuilder
│   └── write.py               # WritePromptBuilder (future)
│
├── validators/                 # Quality validation
│   ├── __init__.py
│   ├── base.py                # BaseValidator
│   ├── structure.py           # Structure validation
│   ├── content.py             # Content quality checks
│   └── generic_phrases.py     # Generic phrase detection
│
├── audit/                      # Logging and versioning
│   ├── __init__.py
│   ├── logger.py              # JSONL audit logger
│   ├── hashing.py             # Stable content hashing
│   └── versioning.py          # Prompt version tracking
│
├── analytics/                  # Metrics and analysis
│   ├── __init__.py
│   ├── metrics.py             # Performance metrics
│   └── reports.py             # Analytics reports
│
├── cli/                        # Command-line interface
│   ├── __init__.py
│   └── commands.py            # CLI commands
│
└── ui/                         # Interactive UI (future)
    ├── __init__.py
    └── app.py                 # Streamlit/Gradio app
```

---

## 📦 Core Components

### 1. Context Retrieval System

**Purpose:** Load scene/project context from database

```python
# lizzy/prompt_studio/context/types.py
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class SceneContext:
    """Complete context for a scene."""
    # Scene data
    scene_id: int
    scene_number: int
    title: str
    description: str
    act: str
    characters: List[str]

    # Surrounding context
    previous_scene: Optional[Dict]
    next_scene: Optional[Dict]
    delta_summary: Optional[str]  # From previous scene

    # Project context
    project_name: str
    genre: str
    logline: Optional[str]
    theme: Optional[str]
    tone: Optional[str]

    # Character bios
    character_bios: List[Dict]

    # Story spine (last 5 scenes)
    story_spine: List[Dict]

    # Existing blueprint (if any)
    blueprint: Optional[str]

    # Metadata
    created_at: str

@dataclass
class ProjectContext:
    """High-level project metadata."""
    name: str
    genre: str
    total_scenes: int
    characters: List[Dict]
    writer_notes: Dict
```

```python
# lizzy/prompt_studio/context/retrieval.py
from pathlib import Path
from typing import Optional
from ..database import Database
from .types import SceneContext, ProjectContext

def load_scene_context(
    db_path: Path,
    scene_number: int,
    include_spine: bool = True,
    include_blueprint: bool = True
) -> SceneContext:
    """
    Load complete context for a scene.

    This is the single source of truth for scene context.
    All prompt builders use this function.
    """
    db = Database(db_path)

    # Load scene
    scene = db.get_scene(scene_number)

    # Load surrounding scenes
    prev_scene = db.get_scene(scene_number - 1) if scene_number > 1 else None
    next_scene = db.get_scene(scene_number + 1)

    # Load delta summary from previous scene
    delta = db.get_delta_summary(scene_number - 1) if prev_scene else None

    # Load project
    project = db.get_project()

    # Load characters (only those in this scene)
    scene_char_names = scene['characters'].split(', ') if scene['characters'] else []
    character_bios = [
        db.get_character(name)
        for name in scene_char_names
    ]

    # Load story spine (last 5 scenes)
    story_spine = []
    if include_spine:
        for i in range(max(1, scene_number - 5), scene_number):
            spine_scene = db.get_scene(i)
            if spine_scene:
                story_spine.append(spine_scene)

    # Load existing blueprint
    blueprint = None
    if include_blueprint:
        blueprint = db.get_scene_blueprint(scene_number)

    return SceneContext(
        scene_id=scene['id'],
        scene_number=scene['scene_number'],
        title=scene['title'],
        description=scene['description'],
        act=scene.get('act', 'Unknown'),
        characters=scene_char_names,
        previous_scene=prev_scene,
        next_scene=next_scene,
        delta_summary=delta,
        project_name=project['name'],
        genre=project['genre'],
        logline=db.get_writer_notes().get('logline'),
        theme=db.get_writer_notes().get('theme'),
        tone=db.get_writer_notes().get('tone'),
        character_bios=character_bios,
        story_spine=story_spine,
        blueprint=blueprint,
        created_at=datetime.now().isoformat()
    )
```

---

### 2. Prompt Templates

**Purpose:** Versioned, reusable prompt templates

```python
# lizzy/prompt_studio/templates/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class PromptMetadata:
    """Metadata for prompt tracking."""
    template_name: str
    version: str
    bucket: str
    hash: str
    created_at: str

class BasePromptTemplate(ABC):
    """Base class for all prompt templates."""

    VERSION = "1.0.0"  # Override in subclasses
    TEMPLATE_NAME = "base"  # Override in subclasses

    @abstractmethod
    def render(self, context: Any) -> str:
        """Render the prompt with given context."""
        pass

    def get_metadata(self, context: Any) -> PromptMetadata:
        """Generate metadata for this prompt."""
        rendered = self.render(context)
        return PromptMetadata(
            template_name=self.TEMPLATE_NAME,
            version=self.VERSION,
            bucket=getattr(self, 'BUCKET', 'unknown'),
            hash=self._hash_content(rendered),
            created_at=datetime.now().isoformat()
        )

    def _hash_content(self, content: str) -> str:
        """Create stable hash of prompt content."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:12]
```

```python
# lizzy/prompt_studio/templates/brainstorm/books.py
from ..base import BasePromptTemplate
from ...context.types import SceneContext

class BooksExpertTemplate(BasePromptTemplate):
    """Books bucket expert template for brainstorming."""

    VERSION = "2.0.0"
    TEMPLATE_NAME = "brainstorm_books"
    BUCKET = "books"

    # Golden-age romcom definition (compressed)
    GOLDEN_AGE_DEF = """GOLDEN-AGE ROMCOM: 1930s-50s screwball/romantic comedies featuring witty rapid-fire dialogue, class conflict, physical comedy, strong independent leads (esp. female), misunderstandings, sophisticated sexual tension (Production Code era). Reference: His Girl Friday, Philadelphia Story, It Happened One Night, Bringing Up Baby."""

    def render(self, context: SceneContext) -> str:
        """Render the Books expert prompt."""

        # Build metadata header
        metadata = f"""---
SCENE_ID: {context.scene_id}
SCENE_NUMBER: {context.scene_number}
ACT: {context.act}
BUCKET: books
MODEL: gpt-4o-mini (LightRAG)
VERSION: {self.VERSION}
PROJECT: {context.project_name}
TIMESTAMP: {context.created_at}
---"""

        # Build story context
        story_context = self._build_story_context(context)

        # Build scene details
        scene_details = self._build_scene_details(context)

        # Build surrounding context
        surrounding = self._build_surrounding_context(context)

        # Assemble prompt
        prompt = f"""{metadata}

You are a SCREENPLAY STRUCTURE AND CRAFT EXPERT consulting on a golden-age romantic comedy.

{self.GOLDEN_AGE_DEF}

{story_context}

{scene_details}

{surrounding}

As a structure expert, PROPOSE how to architect this scene's dramatic structure.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- 5-7 bullets per section
- Target length: 400-800 tokens total
- Active, specific guidance (not theoretical analysis)

**DIRECTIVE:** Extend and critique the surrounding context; do not restate it.

## STRUCTURAL_FUNCTION
Propose where this scene falls structurally and what beat it must hit:
- Three-act position and romcom beat sheet function
- Structural purpose (setup, catalyst, midpoint reversal, crisis, climax)
- How this advances plot threads and character arcs

## BEAT_ENGINEERING
Advise which dramatic beats must occur within this scene:
- Essential turning points and revelations
- Tension escalation or release mechanics
- What must change from scene open to close

## CHARACTER_ARC_MECHANICS
Recommend how character growth manifests:
- Protagonist's internal shift or resistance
- Love interest's evolution
- Supporting character influence

## PACING_AND_RHYTHM
Propose the scene's tempo and structure:
- Opening hook and closing button
- Rising/falling action pattern
- Scene length and density

## SETUP_AND_PAYOFF
Identify what this scene sets up or pays off:
- Callbacks to earlier scenes
- Plants for future scenes
- Promises made to the audience"""

        return prompt

    def _build_story_context(self, context: SceneContext) -> str:
        """Build story context section."""
        parts = [f"PROJECT: {context.project_name}"]

        if context.logline:
            parts.append(f"LOGLINE: {context.logline}")
        if context.theme:
            parts.append(f"THEME: {context.theme}")

        # Character list
        if context.character_bios:
            parts.append("\nCHARACTERS:")
            for char in context.character_bios:
                parts.append(f"  • {char['name']} ({char['role']}): {char['description']}")

        return "STORY CONTEXT:\n" + "\n".join(parts)

    def _build_scene_details(self, context: SceneContext) -> str:
        """Build current scene details."""
        return f"""CURRENT SCENE:
Scene {context.scene_number}: {context.title}
Act: {context.act}
Description: {context.description}
Characters: {', '.join(context.characters)}"""

    def _build_surrounding_context(self, context: SceneContext) -> str:
        """Build surrounding scenes context."""
        parts = ["SURROUNDING SCENES:"]

        if context.delta_summary:
            parts.append(f"Previous: Scene {context.scene_number - 1}")
            parts.append(f"DELTA SUMMARY:\n{context.delta_summary}")
        elif context.previous_scene:
            parts.append(f"Previous: Scene {context.previous_scene['scene_number']}: {context.previous_scene['title']}")
            parts.append(f"{context.previous_scene['description']}")
        else:
            parts.append("Previous: N/A (first scene)")

        if context.next_scene:
            parts.append(f"\nNext: Scene {context.next_scene['scene_number']}: {context.next_scene['title']}")
            parts.append(f"{context.next_scene['description']}")
        else:
            parts.append("\nNext: N/A (final scene)")

        return "\n".join(parts)
```

---

### 3. Prompt Builder

**Purpose:** Construct prompts from templates + context

```python
# lizzy/prompt_studio/builders/brainstorm.py
from typing import Dict, Optional
from pathlib import Path
from ..context.retrieval import load_scene_context
from ..templates.brainstorm.books import BooksExpertTemplate
from ..templates.brainstorm.plays import PlaysExpertTemplate
from ..templates.brainstorm.scripts import ScriptsExpertTemplate
from ..templates.brainstorm.synthesis import SynthesisTemplate
from ..audit.logger import AuditLogger

class BrainstormPromptBuilder:
    """Build brainstorm prompts with full audit trail."""

    def __init__(self, db_path: Path, audit_log_dir: Optional[Path] = None):
        self.db_path = db_path
        self.audit_logger = AuditLogger(audit_log_dir or Path("./prompt_audit"))

        # Initialize templates
        self.templates = {
            'books': BooksExpertTemplate(),
            'plays': PlaysExpertTemplate(),
            'scripts': ScriptsExpertTemplate(),
            'synthesis': SynthesisTemplate()
        }

    def build_expert_prompt(
        self,
        scene_number: int,
        bucket: str
    ) -> Dict:
        """
        Build a single expert prompt.

        Returns:
            {
                'prompt': str,
                'metadata': PromptMetadata,
                'context': SceneContext
            }
        """
        # Load context
        context = load_scene_context(self.db_path, scene_number)

        # Get template
        template = self.templates.get(bucket)
        if not template:
            raise ValueError(f"Unknown bucket: {bucket}")

        # Render prompt
        prompt = template.render(context)
        metadata = template.get_metadata(context)

        # Log to audit trail
        self.audit_logger.log_prompt_generation(
            scene_number=scene_number,
            bucket=bucket,
            prompt_hash=metadata.hash,
            template_version=metadata.version
        )

        return {
            'prompt': prompt,
            'metadata': metadata,
            'context': context
        }

    def build_synthesis_prompt(
        self,
        scene_number: int,
        expert_responses: Dict[str, str]
    ) -> Dict:
        """Build synthesis prompt from expert responses."""
        context = load_scene_context(self.db_path, scene_number)

        template = self.templates['synthesis']
        prompt = template.render(context, expert_responses)
        metadata = template.get_metadata(context)

        return {
            'prompt': prompt,
            'metadata': metadata,
            'context': context
        }

    def preview_all_prompts(self, scene_number: int) -> Dict:
        """Generate all prompts for a scene without calling LLM."""
        prompts = {}

        for bucket in ['books', 'plays', 'scripts']:
            prompts[bucket] = self.build_expert_prompt(scene_number, bucket)

        return prompts

    def save_prompt_preview(
        self,
        scene_number: int,
        output_dir: Path
    ) -> None:
        """Save all prompts to markdown files for review."""
        prompts = self.preview_all_prompts(scene_number)

        output_dir.mkdir(parents=True, exist_ok=True)

        for bucket, prompt_data in prompts.items():
            output_file = output_dir / f"Scene{scene_number:02d}_{bucket}.md"

            with open(output_file, 'w') as f:
                f.write(f"# Scene {scene_number} - {bucket.upper()} Expert Prompt\n\n")
                f.write(f"**Version:** {prompt_data['metadata'].version}\n")
                f.write(f"**Hash:** {prompt_data['metadata'].hash}\n")
                f.write(f"**Created:** {prompt_data['metadata'].created_at}\n\n")
                f.write("---\n\n")
                f.write(prompt_data['prompt'])

            print(f"✅ Saved: {output_file}")
```

---

### 4. Quality Validation

**Purpose:** Validate LLM responses for quality

```python
# lizzy/prompt_studio/validators/content.py
from typing import List, Dict
import re

class ContentValidator:
    """Validate response content quality."""

    # Generic phrases that indicate low-quality output
    GENERIC_PHRASES = [
        "raise the stakes",
        "add tension",
        "create conflict",
        "build suspense",
        "increase drama",
        "show don't tell",
        "make it compelling",
        "add depth",
        "enhance the scene",
        "make it more interesting"
    ]

    def validate_response(
        self,
        response: str,
        context: 'SceneContext',
        bucket: str
    ) -> Dict:
        """
        Validate an LLM response.

        Returns:
            {
                'valid': bool,
                'score': float (0-1),
                'issues': List[str],
                'warnings': List[str]
            }
        """
        issues = []
        warnings = []
        score = 1.0

        # Check for generic phrases
        generic_found = self._check_generic_phrases(response)
        if generic_found:
            warnings.append(f"Contains generic phrases: {', '.join(generic_found[:3])}")
            score -= 0.2

        # Check for character name references
        char_refs = self._check_character_references(response, context.characters)
        if not char_refs:
            issues.append("No character names referenced")
            score -= 0.3

        # Check for specific scene references
        if context.title.lower() not in response.lower():
            warnings.append("Scene title not referenced")
            score -= 0.1

        # Check response length
        word_count = len(response.split())
        if word_count < 200:
            issues.append(f"Response too short: {word_count} words")
            score -= 0.2
        elif word_count > 1000:
            warnings.append(f"Response very long: {word_count} words")

        # Bucket-specific validation
        bucket_issues = self._validate_bucket_specific(response, bucket)
        issues.extend(bucket_issues)
        score -= len(bucket_issues) * 0.1

        return {
            'valid': len(issues) == 0,
            'score': max(0, score),
            'issues': issues,
            'warnings': warnings,
            'character_refs': char_refs,
            'word_count': word_count
        }

    def _check_generic_phrases(self, text: str) -> List[str]:
        """Find generic phrases in response."""
        found = []
        text_lower = text.lower()

        for phrase in self.GENERIC_PHRASES:
            if phrase in text_lower:
                found.append(phrase)

        return found

    def _check_character_references(
        self,
        text: str,
        character_names: List[str]
    ) -> List[str]:
        """Find character name references."""
        found = []

        for name in character_names:
            if name in text:
                found.append(name)

        return found

    def _validate_bucket_specific(
        self,
        response: str,
        bucket: str
    ) -> List[str]:
        """Bucket-specific validation rules."""
        issues = []

        if bucket == 'books':
            # Should mention structure
            if 'structural' not in response.lower() and 'structure' not in response.lower():
                issues.append("Books expert should discuss structure")

        elif bucket == 'plays':
            # Should mention dialogue
            if 'dialogue' not in response.lower():
                issues.append("Plays expert should discuss dialogue")

        elif bucket == 'scripts':
            # Should mention visual
            if 'visual' not in response.lower():
                issues.append("Scripts expert should discuss visual elements")

        return issues
```

---

### 5. Audit Trail

**Purpose:** Complete logging for reproducibility

```python
# lizzy/prompt_studio/audit/logger.py
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class AuditLogger:
    """JSONL audit logging for all prompt operations."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def log_prompt_generation(
        self,
        scene_number: int,
        bucket: str,
        prompt_hash: str,
        template_version: str,
        **kwargs
    ) -> None:
        """Log prompt generation event."""
        entry = {
            'event': 'prompt_generated',
            'timestamp': datetime.now().isoformat(),
            'scene_number': scene_number,
            'bucket': bucket,
            'prompt_hash': prompt_hash,
            'template_version': template_version,
            **kwargs
        }
        self._write_entry(entry)

    def log_llm_call(
        self,
        scene_number: int,
        bucket: str,
        prompt_hash: str,
        model: str,
        elapsed_ms: float,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        **kwargs
    ) -> None:
        """Log LLM API call."""
        entry = {
            'event': 'llm_call',
            'timestamp': datetime.now().isoformat(),
            'scene_number': scene_number,
            'bucket': bucket,
            'prompt_hash': prompt_hash,
            'model': model,
            'elapsed_ms': elapsed_ms,
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'cost_usd': cost,
            **kwargs
        }
        self._write_entry(entry)

    def log_validation(
        self,
        scene_number: int,
        bucket: str,
        valid: bool,
        score: float,
        issues: List[str],
        warnings: List[str],
        **kwargs
    ) -> None:
        """Log validation result."""
        entry = {
            'event': 'validation',
            'timestamp': datetime.now().isoformat(),
            'scene_number': scene_number,
            'bucket': bucket,
            'valid': valid,
            'score': score,
            'issues': issues,
            'warnings': warnings,
            **kwargs
        }
        self._write_entry(entry)

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write entry to JSONL file."""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

---

### 6. CLI Interface

**Purpose:** Command-line tools for developers

```python
# lizzy/prompt_studio/cli/commands.py
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from ..builders.brainstorm import BrainstormPromptBuilder

console = Console()

@click.group()
def cli():
    """Lizzy Prompt Studio - Prompt management and testing."""
    pass

@cli.command()
@click.option('--project', required=True, help='Project name')
@click.option('--scene', type=int, required=True, help='Scene number')
@click.option('--bucket', type=click.Choice(['books', 'plays', 'scripts', 'all']), default='all')
@click.option('--output-dir', type=Path, default=Path('./prompt_previews'))
def preview(project: str, scene: int, bucket: str, output_dir: Path):
    """Generate prompt previews without calling LLM."""
    from lizzy.start import StartModule

    # Get project database
    start = StartModule()
    db_path = start.get_project_path(project)

    if not db_path:
        console.print(f"[red]Project '{project}' not found[/red]")
        return

    # Build prompts
    builder = BrainstormPromptBuilder(db_path)

    if bucket == 'all':
        console.print(f"[cyan]Generating all prompts for Scene {scene}...[/cyan]\n")
        builder.save_prompt_preview(scene, output_dir)
    else:
        console.print(f"[cyan]Generating {bucket} prompt for Scene {scene}...[/cyan]\n")
        prompt_data = builder.build_expert_prompt(scene, bucket)

        output_file = output_dir / f"Scene{scene:02d}_{bucket}.md"
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(prompt_data['prompt'])

        console.print(f"[green]✓ Saved: {output_file}[/green]")

@cli.command()
@click.option('--project', required=True, help='Project name')
@click.option('--scene', type=int, required=True, help='Scene number')
@click.option('--bucket', type=click.Choice(['books', 'plays', 'scripts']), required=True)
@click.argument('response_file', type=Path)
def validate(project: str, scene: int, bucket: str, response_file: Path):
    """Validate an LLM response."""
    from lizzy.start import StartModule
    from ..context.retrieval import load_scene_context
    from ..validators.content import ContentValidator

    # Get project database
    start = StartModule()
    db_path = start.get_project_path(project)

    # Load response
    response = response_file.read_text()

    # Load context
    context = load_scene_context(db_path, scene)

    # Validate
    validator = ContentValidator()
    result = validator.validate_response(response, context, bucket)

    # Display results
    console.print(f"\n[bold]Validation Results for Scene {scene} ({bucket})[/bold]\n")

    if result['valid']:
        console.print("[green]✓ VALID[/green]")
    else:
        console.print("[red]✗ INVALID[/red]")

    console.print(f"Score: {result['score']:.2f}/1.0")
    console.print(f"Word count: {result['word_count']}")
    console.print(f"Character refs: {', '.join(result['character_refs'])}")

    if result['issues']:
        console.print("\n[red]Issues:[/red]")
        for issue in result['issues']:
            console.print(f"  • {issue}")

    if result['warnings']:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result['warnings']:
            console.print(f"  • {warning}")

@cli.command()
@click.option('--log-dir', type=Path, default=Path('./prompt_audit'))
@click.option('--days', type=int, default=7, help='Days to analyze')
def stats(log_dir: Path, days: int):
    """Show audit log statistics."""
    import json
    from datetime import datetime, timedelta
    from collections import defaultdict

    # Collect stats
    stats = defaultdict(lambda: {
        'total_prompts': 0,
        'total_calls': 0,
        'total_validations': 0,
        'avg_score': [],
        'total_cost': 0.0,
        'avg_latency': []
    })

    # Read JSONL files
    cutoff = datetime.now() - timedelta(days=days)

    for log_file in log_dir.glob('audit_*.jsonl'):
        with open(log_file) as f:
            for line in f:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry['timestamp'])

                if ts < cutoff:
                    continue

                bucket = entry.get('bucket', 'unknown')

                if entry['event'] == 'prompt_generated':
                    stats[bucket]['total_prompts'] += 1
                elif entry['event'] == 'llm_call':
                    stats[bucket]['total_calls'] += 1
                    stats[bucket]['total_cost'] += entry.get('cost_usd', 0)
                    stats[bucket]['avg_latency'].append(entry.get('elapsed_ms', 0))
                elif entry['event'] == 'validation':
                    stats[bucket]['total_validations'] += 1
                    stats[bucket]['avg_score'].append(entry.get('score', 0))

    # Display table
    table = Table(title=f"Prompt Studio Stats (Last {days} days)")
    table.add_column("Bucket")
    table.add_column("Prompts")
    table.add_column("LLM Calls")
    table.add_column("Avg Score")
    table.add_column("Avg Latency")
    table.add_column("Total Cost")

    for bucket, data in sorted(stats.items()):
        avg_score = sum(data['avg_score']) / len(data['avg_score']) if data['avg_score'] else 0
        avg_latency = sum(data['avg_latency']) / len(data['avg_latency']) if data['avg_latency'] else 0

        table.add_row(
            bucket,
            str(data['total_prompts']),
            str(data['total_calls']),
            f"{avg_score:.2f}",
            f"{avg_latency:.0f}ms",
            f"${data['total_cost']:.2f}"
        )

    console.print(table)

if __name__ == '__main__':
    cli()
```

---

## 🎨 Usage Examples

### 1. Preview Prompts Before Running
```bash
# Preview all prompts for Scene 5
python -m lizzy.prompt_studio preview --project "My Romcom" --scene 5 --bucket all

# Output: prompt_previews/Scene05_books.md
#         prompt_previews/Scene05_plays.md
#         prompt_previews/Scene05_scripts.md
```

### 2. Validate LLM Response
```bash
# Validate a response for quality
python -m lizzy.prompt_studio validate \
    --project "My Romcom" \
    --scene 5 \
    --bucket books \
    response.txt

# Output:
# ✓ VALID
# Score: 0.85/1.0
# Word count: 523
# Character refs: Margaret, Andrew
#
# Warnings:
#   • Contains generic phrase: "raise the stakes"
```

### 3. View Analytics
```bash
# Show stats for last 7 days
python -m lizzy.prompt_studio stats --days 7

# Output table:
# ┌────────┬─────────┬───────────┬───────────┬─────────────┬────────────┐
# │ Bucket │ Prompts │ LLM Calls │ Avg Score │ Avg Latency │ Total Cost │
# ├────────┼─────────┼───────────┼───────────┼─────────────┼────────────┤
# │ books  │ 30      │ 30        │ 0.87      │ 2340ms      │ $0.45      │
# │ plays  │ 30      │ 30        │ 0.82      │ 2180ms      │ $0.42      │
# │ scripts│ 30      │ 30        │ 0.89      │ 2520ms      │ $0.48      │
# └────────┴─────────┴───────────┴───────────┴─────────────┴────────────┘
```

---

## 📊 Features Roadmap

### Phase 1: Core Infrastructure (Week 1) ✅
- [x] Context retrieval system
- [x] Base template classes
- [x] Prompt builders
- [x] Audit logging

### Phase 2: Templates & Validation (Week 2)
- [ ] All brainstorm templates (books, plays, scripts, synthesis)
- [ ] Content validators
- [ ] Generic phrase detection
- [ ] Bucket-specific validation

### Phase 3: CLI Tools (Week 3)
- [ ] Preview command
- [ ] Validate command
- [ ] Stats command
- [ ] Diff command (compare prompt versions)

### Phase 4: Analytics (Week 4)
- [ ] Performance metrics
- [ ] Cost tracking
- [ ] Quality trends
- [ ] A/B testing framework

### Phase 5: Visual UI (Future)
- [ ] Streamlit/Gradio interface
- [ ] Visual prompt editor
- [ ] Real-time preview
- [ ] Interactive validation

---

## 🎯 Benefits

### For Development
✅ **Consistent prompts** - Single source of truth
✅ **Version control** - Track prompt changes over time
✅ **Reproducibility** - Same context = same prompt
✅ **Testing** - Validate without API calls

### For Production
✅ **Quality assurance** - Automated validation
✅ **Cost tracking** - Monitor API spending
✅ **Performance** - Measure latency and throughput
✅ **Audit trail** - Complete logging

### For Research
✅ **A/B testing** - Compare prompt variations
✅ **Analytics** - Identify what works
✅ **Optimization** - Improve prompts over time
✅ **Metrics** - Measure quality objectively

---

## 🔧 Integration with Current System

### Automated Brainstorm Integration
```python
# In lizzy/automated_brainstorm.py

from lizzy.prompt_studio.builders.brainstorm import BrainstormPromptBuilder

class AutomatedBrainstorm:
    def __init__(self, db_path: Path):
        # ... existing code ...

        # Add prompt studio
        self.prompt_builder = BrainstormPromptBuilder(
            db_path=db_path,
            audit_log_dir=Path("./prompt_audit")
        )

    def build_expert_query(self, scene: Dict, bucket_name: str) -> str:
        """Use Prompt Studio instead of inline prompts."""
        prompt_data = self.prompt_builder.build_expert_prompt(
            scene_number=scene['scene_number'],
            bucket=bucket_name
        )

        # Log metadata
        self.prompt_metadata[scene['scene_number']][bucket_name] = prompt_data['metadata']

        return prompt_data['prompt']
```

---

## 📁 File Structure After Implementation

```
LIZZY_ROMCOM/
├── lizzy/
│   ├── prompt_studio/          # NEW
│   │   ├── context/
│   │   ├── templates/
│   │   ├── builders/
│   │   ├── validators/
│   │   ├── audit/
│   │   ├── analytics/
│   │   └── cli/
│   ├── automated_brainstorm.py # MODIFIED (uses Prompt Studio)
│   ├── interactive_brainstorm.py # MODIFIED (uses Prompt Studio)
│   └── ...
│
├── prompt_audit/               # NEW (JSONL logs)
├── prompt_previews/            # NEW (saved prompts)
└── ...
```

---

**Next Step:** Would you like me to implement Phase 1 (Core Infrastructure) or start with a specific component?
