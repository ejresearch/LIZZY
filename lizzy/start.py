"""
START Module - Project Initialization

Purpose: Initializes new writing projects by creating a dedicated SQLite database.

From Lizzy White Paper:
"Sets up isolated tables for characters, outlines, brainstorming logs, and
final drafts. Ensures data encapsulation and project independence."

Impact: Provides a solid, organized foundation for every project, regardless
of the writing form.
"""

from pathlib import Path
from typing import Optional, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from .database import Database

console = Console()


# Universal 30-scene romcom beat sheet
ROMCOM_BEAT_SHEET = {
    "name": "Romcom Beat Sheet (30 Scenes)",
    "description": "Universal romantic comedy structure - customize each scene to your story",
    "characters": [
        {
            "name": "Protagonist",
            "description": "Lead character on a journey to love",
            "role": "protagonist"
        },
        {
            "name": "Love Interest",
            "description": "The romantic partner",
            "role": "love_interest"
        },
        {
            "name": "Best Friend",
            "description": "Confidant and voice of reason",
            "role": "supporting"
        },
        {
            "name": "Obstacle",
            "description": "Person or force creating conflict",
            "role": "antagonist"
        }
    ],
    "scenes": [
        # ACT 1 (Pages 1-30)
        {"number": 1, "title": "Opening Image", "description": "Show protagonist's world before love changes everything", "act": 1},
        {"number": 2, "title": "Theme Stated", "description": "Hint at what protagonist needs to learn about love", "act": 1},
        {"number": 3, "title": "Setup", "description": "Establish protagonist's life, flaw, and what's missing", "act": 1},
        {"number": 4, "title": "Catalyst", "description": "Event that sets the romantic story in motion", "act": 1},
        {"number": 5, "title": "Debate", "description": "Protagonist resists change or new relationship", "act": 1},
        {"number": 6, "title": "Break into Two", "description": "Decision to pursue romance or enter new situation", "act": 1},

        # ACT 2A (Pages 30-60)
        {"number": 7, "title": "B Story Begins", "description": "Introduction of relationship that mirrors main romance", "act": 2},
        {"number": 8, "title": "Fun and Games", "description": "Romantic premise delivered - dating, flirting, chemistry", "act": 2},
        {"number": 9, "title": "First Date/Encounter", "description": "Initial romantic interaction sets tone", "act": 2},
        {"number": 10, "title": "Building Connection", "description": "Shared experiences create bond", "act": 2},
        {"number": 11, "title": "Obstacles Appear", "description": "First signs of conflict or incompatibility", "act": 2},
        {"number": 12, "title": "Deepening Romance", "description": "Intimacy increases despite obstacles", "act": 2},
        {"number": 13, "title": "Vulnerability Moment", "description": "One character reveals deeper truth", "act": 2},
        {"number": 14, "title": "Midpoint", "description": "False high - relationship seems perfect OR major revelation", "act": 2},
        {"number": 15, "title": "Commitment Shift", "description": "Stakes raise - relationship becomes more serious", "act": 2},

        # ACT 2B (Pages 60-90)
        {"number": 16, "title": "Bad Guys Close In", "description": "External pressures threaten relationship", "act": 2},
        {"number": 17, "title": "Doubt Creeps In", "description": "Internal fears surface", "act": 2},
        {"number": 18, "title": "Jealousy/Misunderstanding", "description": "Conflict arises from insecurity or miscommunication", "act": 2},
        {"number": 19, "title": "Old Wounds", "description": "Past trauma or patterns emerge", "act": 2},
        {"number": 20, "title": "Relationship Tested", "description": "Major challenge to the romance", "act": 2},
        {"number": 21, "title": "Attempt to Fix", "description": "One character tries to salvage relationship", "act": 2},
        {"number": 22, "title": "All Is Lost", "description": "Relationship appears to end - worst possible outcome", "act": 2},
        {"number": 23, "title": "Dark Night of Soul", "description": "Protagonist alone, heartbroken, questioning everything", "act": 2},
        {"number": 24, "title": "Realization", "description": "Protagonist understands what they truly need", "act": 2},

        # ACT 3 (Pages 90-110)
        {"number": 25, "title": "Break into Three", "description": "Decision to fight for love with new understanding", "act": 3},
        {"number": 26, "title": "Gathering Allies", "description": "Friends/support help with plan", "act": 3},
        {"number": 27, "title": "Finale Begins", "description": "Protagonist takes action to win love back", "act": 3},
        {"number": 28, "title": "Grand Gesture", "description": "Public or private declaration proving growth", "act": 3},
        {"number": 29, "title": "Love Interest Response", "description": "Romantic partner must choose to forgive/accept", "act": 3},
        {"number": 30, "title": "Final Image", "description": "Together - mirror of opening but transformed by love", "act": 3}
    ]
}

# Romcom project templates (DEPRECATED - kept for backwards compatibility)
TEMPLATES = {
    "enemies_to_lovers": {
        "name": "Enemies to Lovers",
        "description": "Rivals forced into proximity discover attraction beneath antagonism",
        "characters": [
            {
                "name": "Character A",
                "description": "Someone with power or status who maintains emotional distance",
                "role": "protagonist"
            },
            {
                "name": "Character B",
                "description": "Competent person in subordinate or rival position",
                "role": "love_interest"
            },
            {
                "name": "Character C",
                "description": "Friend or colleague who observes their dynamic",
                "role": "supporting"
            },
            {
                "name": "Character D",
                "description": "Authority figure who creates forced collaboration",
                "role": "supporting"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "Establish conflict",
                "description": "Introduce the antagonistic dynamic and power imbalance",
                "characters": "Character A, Character B"
            },
            {
                "number": 2,
                "title": "Force proximity",
                "description": "External circumstances require them to work together",
                "characters": "Character A, Character B, Character D"
            },
            {
                "number": 3,
                "title": "Shift in perception",
                "description": "A moment reveals unexpected depth or vulnerability",
                "characters": "Character A, Character B"
            },
            {
                "number": 4,
                "title": "External perspective",
                "description": "Observer highlights chemistry they're denying",
                "characters": "Character A, Character C"
            },
            {
                "number": 5,
                "title": "Undeniable tension",
                "description": "Emotional or physical tension becomes impossible to ignore",
                "characters": "Character A, Character B"
            }
        ]
    },
    "fake_relationship": {
        "name": "Fake Relationship",
        "description": "A transactional arrangement develops into genuine feelings",
        "characters": [
            {
                "name": "Character A",
                "description": "Someone facing external pressure requiring a partner",
                "role": "protagonist"
            },
            {
                "name": "Character B",
                "description": "Willing participant with their own agenda",
                "role": "love_interest"
            },
            {
                "name": "Character C",
                "description": "Friend who questions the wisdom of the arrangement",
                "role": "supporting"
            },
            {
                "name": "Character D",
                "description": "Source of pressure or person to be convinced",
                "role": "antagonist"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "Establish the problem",
                "description": "Introduce the external pressure or crisis",
                "characters": "Character A, Character C"
            },
            {
                "number": 2,
                "title": "Negotiate arrangement",
                "description": "Define terms, boundaries, and mutual benefits",
                "characters": "Character A, Character B"
            },
            {
                "number": 3,
                "title": "First performance",
                "description": "Test the arrangement in front of others",
                "characters": "Character A, Character B, Character D"
            },
            {
                "number": 4,
                "title": "Define boundaries",
                "description": "Establish rules about emotional involvement",
                "characters": "Character A, Character B"
            },
            {
                "number": 5,
                "title": "Blur the lines",
                "description": "A moment where pretense gives way to authenticity",
                "characters": "Character A, Character B"
            }
        ]
    },
    "second_chance": {
        "name": "Second Chance Romance",
        "description": "Former lovers reunite and face what drove them apart",
        "characters": [
            {
                "name": "Character A",
                "description": "Ex-partner who appears to have moved forward",
                "role": "protagonist"
            },
            {
                "name": "Character B",
                "description": "Ex-partner carrying unresolved feelings",
                "role": "love_interest"
            },
            {
                "name": "Character C",
                "description": "Mutual connection who maintains ties to both",
                "role": "supporting"
            },
            {
                "name": "Character D",
                "description": "Current partner representing the safer path",
                "role": "antagonist"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "Unexpected reunion",
                "description": "Former partners encounter each other after separation",
                "characters": "Character A, Character B, Character C"
            },
            {
                "number": 2,
                "title": "Resurface tension",
                "description": "Unresolved issues from the past emerge",
                "characters": "Character A, Character B"
            },
            {
                "number": 3,
                "title": "Present complications",
                "description": "Current circumstances create conflict with past feelings",
                "characters": "Character A, Character D, Character B"
            },
            {
                "number": 4,
                "title": "Address the past",
                "description": "Confront the real reason the relationship ended",
                "characters": "Character A, Character B"
            },
            {
                "number": 5,
                "title": "Make a choice",
                "description": "Decide between familiar comfort and rekindled love",
                "characters": "Character A, Character C"
            }
        ]
    },
    "opposites_attract": {
        "name": "Opposites Attract",
        "description": "Contrasting personalities discover complementary strengths",
        "characters": [
            {
                "name": "Character A",
                "description": "Someone who values order, planning, or tradition",
                "role": "protagonist"
            },
            {
                "name": "Character B",
                "description": "Someone who values spontaneity, change, or innovation",
                "role": "love_interest"
            },
            {
                "name": "Character C",
                "description": "Neutral party who sees value in both perspectives",
                "role": "supporting"
            },
            {
                "name": "Character D",
                "description": "Person representing the expected or conventional choice",
                "role": "supporting"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "Establish contrast",
                "description": "Incompatible values or approaches create initial conflict",
                "characters": "Character A, Character B"
            },
            {
                "number": 2,
                "title": "Require cooperation",
                "description": "External circumstances demand they collaborate",
                "characters": "Character A, Character B, Character C"
            },
            {
                "number": 3,
                "title": "Experience the other",
                "description": "One character enters the other's world",
                "characters": "Character A, Character B"
            },
            {
                "number": 4,
                "title": "Present the alternative",
                "description": "Reminder of the safer, more compatible option",
                "characters": "Character A, Character D"
            },
            {
                "number": 5,
                "title": "Discover harmony",
                "description": "Realize differences create balance rather than conflict",
                "characters": "Character A, Character B"
            }
        ]
    }
}

# Preset examples - specific implementations ready to customize
PRESET_TEMPLATES = {
    "the_proposal_preset": {
        "name": "The Proposal (Preset Example)",
        "description": "Powerful boss and employee in fake engagement - specific example to customize",
        "characters": [
            {
                "name": "Margaret",
                "description": "High-powered publishing executive facing deportation",
                "role": "protagonist"
            },
            {
                "name": "Andrew",
                "description": "Long-suffering assistant with publishing ambitions",
                "role": "love_interest"
            },
            {
                "name": "Gertrude",
                "description": "Andrew's quirky grandmother who sees through the charade",
                "role": "supporting"
            },
            {
                "name": "Mr. Gilbertson",
                "description": "Suspicious immigration officer investigating the engagement",
                "role": "supporting"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "The Deportation Crisis",
                "description": "Margaret learns she's being deported and forces Andrew into a fake engagement",
                "characters": "Margaret, Andrew"
            },
            {
                "number": 2,
                "title": "Immigration Interrogation",
                "description": "Mr. Gilbertson questions them separately about their relationship",
                "characters": "Margaret, Andrew, Mr. Gilbertson"
            },
            {
                "number": 3,
                "title": "Meeting the Family",
                "description": "They travel to Alaska where family dynamics expose vulnerabilities",
                "characters": "Margaret, Andrew, Gertrude"
            },
            {
                "number": 4,
                "title": "The Birthday Celebration",
                "description": "Forced intimacy at family party leads to unexpected connection",
                "characters": "Margaret, Andrew, Gertrude"
            },
            {
                "number": 5,
                "title": "The Almost Wedding",
                "description": "At the altar, truth comes out and real feelings emerge",
                "characters": "Margaret, Andrew"
            }
        ],
        "act_structure": {
            "act_1": [1, 2],
            "act_2": [3, 4],
            "act_3": [5]
        }
    },
    "to_all_the_boys_preset": {
        "name": "To All The Boys (Preset Example)",
        "description": "Fake dating to make others jealous - specific example to customize",
        "characters": [
            {
                "name": "Lara Jean",
                "description": "Romantic dreamer whose secret love letters get mailed",
                "role": "protagonist"
            },
            {
                "name": "Peter",
                "description": "Popular jock who suggests fake dating arrangement",
                "role": "love_interest"
            },
            {
                "name": "Chris",
                "description": "Best friend who is skeptical of the fake relationship",
                "role": "supporting"
            },
            {
                "name": "Gen",
                "description": "Peter's ex-girlfriend who Lara Jean wants to avoid",
                "role": "antagonist"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "Letters Exposed",
                "description": "Lara Jean's secret love letters are mysteriously mailed out",
                "characters": "Lara Jean, Chris"
            },
            {
                "number": 2,
                "title": "The Contract",
                "description": "Peter proposes fake dating to make Gen jealous",
                "characters": "Lara Jean, Peter"
            },
            {
                "number": 3,
                "title": "Going Public",
                "description": "First day as fake couple at school creates complications",
                "characters": "Lara Jean, Peter, Gen"
            },
            {
                "number": 4,
                "title": "The Ski Trip",
                "description": "Close quarters and jealousy blur the boundaries",
                "characters": "Lara Jean, Peter"
            },
            {
                "number": 5,
                "title": "Real or Fake",
                "description": "Confronting whether feelings have become genuine",
                "characters": "Lara Jean, Peter, Chris"
            }
        ],
        "act_structure": {
            "act_1": [1, 2],
            "act_2": [3, 4],
            "act_3": [5]
        }
    },
    "when_harry_met_sally_preset": {
        "name": "When Harry Met Sally (Preset Example)",
        "description": "Friends reunite over years and fall in love - specific example to customize",
        "characters": [
            {
                "name": "Sally",
                "description": "Particular, organized woman navigating relationships and career",
                "role": "protagonist"
            },
            {
                "name": "Harry",
                "description": "Cynical man who believes men and women can't be friends",
                "role": "love_interest"
            },
            {
                "name": "Marie",
                "description": "Sally's best friend dating Harry's best friend",
                "role": "supporting"
            },
            {
                "name": "Joe",
                "description": "Sally's ex-boyfriend who represents her past",
                "role": "antagonist"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "The Road Trip",
                "description": "Harry and Sally meet and debate whether men and women can be friends",
                "characters": "Sally, Harry"
            },
            {
                "number": 2,
                "title": "Years Later Reunion",
                "description": "Chance airport meeting after both have been through breakups",
                "characters": "Sally, Harry"
            },
            {
                "number": 3,
                "title": "Building Friendship",
                "description": "Late night phone calls and walks establish deep connection",
                "characters": "Sally, Harry, Marie"
            },
            {
                "number": 4,
                "title": "Sleeping Together",
                "description": "One night together threatens to ruin the friendship",
                "characters": "Sally, Harry"
            },
            {
                "number": 5,
                "title": "New Year's Eve",
                "description": "Harry realizes he loves Sally and makes a declaration",
                "characters": "Sally, Harry"
            }
        ],
        "act_structure": {
            "act_1": [1, 2],
            "act_2": [3, 4],
            "act_3": [5]
        }
    },
    "youve_got_mail_preset": {
        "name": "You've Got Mail (Preset Example)",
        "description": "Business rivals who are anonymous online friends - specific example to customize",
        "characters": [
            {
                "name": "Kathleen",
                "description": "Owner of small independent bookshop fighting to survive",
                "role": "protagonist"
            },
            {
                "name": "Joe",
                "description": "Corporate bookstore exec who is unknowingly her online pen pal",
                "role": "love_interest"
            },
            {
                "name": "Christina",
                "description": "Kathleen's employee and friend at the bookshop",
                "role": "supporting"
            },
            {
                "name": "Frank",
                "description": "Kathleen's boyfriend who represents her current life",
                "role": "supporting"
            }
        ],
        "scenes": [
            {
                "number": 1,
                "title": "Online Connection",
                "description": "Kathleen and Joe bond anonymously via email while living separate lives",
                "characters": "Kathleen, Joe"
            },
            {
                "number": 2,
                "title": "Business Clash",
                "description": "Joe's megastore threatens Kathleen's independent bookshop",
                "characters": "Kathleen, Joe, Christina"
            },
            {
                "number": 3,
                "title": "The Bookshop Closes",
                "description": "Kathleen loses her store but continues email friendship",
                "characters": "Kathleen, Christina"
            },
            {
                "number": 4,
                "title": "Identity Revealed",
                "description": "Joe discovers online friend is his business rival",
                "characters": "Kathleen, Joe"
            },
            {
                "number": 5,
                "title": "The Meeting",
                "description": "Final email meetup where Kathleen learns the truth",
                "characters": "Kathleen, Joe"
            }
        ],
        "act_structure": {
            "act_1": [1, 2],
            "act_2": [3, 4],
            "act_3": [5]
        }
    }
}


class StartModule:
    """
    Handles project initialization and database creation.

    Each project gets:
    - Isolated SQLite database
    - Dedicated project directory
    - Initialized schema for all modules
    """

    def __init__(self, projects_dir: Path = Path("./projects")):
        """
        Initialize Start module.

        Args:
            projects_dir: Directory where project databases are stored
        """
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        name: str,
        genre: str = "Romantic Comedy",
        description: str = ""
    ) -> Path:
        """
        Create a new project with isolated database.

        Args:
            name: Project name (will be sanitized for filesystem)
            genre: Genre/type of screenplay
            description: Optional project description

        Returns:
            Path to created database file

        Raises:
            ValueError: If project already exists

        Example:
            start = StartModule()
            db_path = start.create_project(
                name="The Proposal 2.0",
                genre="Romantic Comedy",
                description="Career-driven CEO needs fake fiancé"
            )
        """
        # Sanitize project name for filesystem
        safe_name = self._sanitize_name(name)

        # Create project directory
        project_dir = self.projects_dir / safe_name
        if project_dir.exists():
            raise ValueError(f"Project '{name}' already exists at {project_dir}")

        project_dir.mkdir(parents=True, exist_ok=True)

        # Create database
        db_path = project_dir / f"{safe_name}.db"
        db = Database(db_path)

        # Initialize schema
        db.initialize_schema()

        # Welcome panel
        console.print(Panel.fit(
            f"[bold cyan]New Project: {name}[/bold cyan]\n\n"
            f"Genre: {genre}\n"
            f"Description: {description or '(none)'}",
            border_style="cyan"
        ))

        # Create database with status
        with console.status("[cyan]Initializing database schema..."):
            db.initialize_schema()
            db.insert_project(name=name, genre=genre, description=description)

        # Success tree
        tree = Tree("[bold green]Project Created Successfully")
        tree.add(f"Location: {project_dir}")
        db_node = tree.add("Database Schema")
        db_node.add("projects [dim](1 row)[/dim]")
        db_node.add("characters [dim](empty)[/dim]")
        db_node.add("scenes [dim](empty)[/dim]")
        db_node.add("brainstorm_sessions [dim](empty)[/dim]")
        db_node.add("drafts [dim](empty)[/dim]")

        console.print("\n")
        console.print(tree)

        return db_path

    def create_from_template(
        self,
        name: str,
        template_key: str,
        genre: str = "Romantic Comedy"
    ) -> Path:
        """
        Create a new project from a romcom template.

        Args:
            name: Project name (will be sanitized for filesystem)
            template_key: Template identifier (e.g., 'enemies_to_lovers')
            genre: Genre/type of screenplay

        Returns:
            Path to created database file

        Raises:
            ValueError: If project exists or template not found

        Example:
            start = StartModule()
            db_path = start.create_from_template(
                name="My Romcom",
                template_key="fake_relationship"
            )
        """
        # Validate template
        if template_key not in TEMPLATES:
            valid_keys = ", ".join(TEMPLATES.keys())
            raise ValueError(f"Template '{template_key}' not found. Valid templates: {valid_keys}")

        template = TEMPLATES[template_key]

        # Sanitize project name
        safe_name = self._sanitize_name(name)

        # Create project directory
        project_dir = self.projects_dir / safe_name
        if project_dir.exists():
            raise ValueError(f"Project '{name}' already exists at {project_dir}")

        project_dir.mkdir(parents=True, exist_ok=True)

        # Create database
        db_path = project_dir / f"{safe_name}.db"
        db = Database(db_path)

        # Welcome panel
        console.print(Panel.fit(
            f"[bold cyan]New Project from Template[/bold cyan]\n\n"
            f"Project: {name}\n"
            f"Template: {template['name']}\n"
            f"Description: {template['description']}",
            border_style="cyan"
        ))

        # Initialize schema and project
        with console.status("[cyan]Initializing database schema..."):
            db.initialize_schema()
            db.insert_project(
                name=name,
                genre=genre,
                description=template['description']
            )

        # Populate characters
        with console.status("[cyan]Adding template characters..."):
            with db.get_connection() as conn:
                cursor = conn.cursor()
                for char in template['characters']:
                    cursor.execute(
                        "INSERT INTO characters (name, description, role) VALUES (?, ?, ?)",
                        (char['name'], char['description'], char['role'])
                    )

        # Populate scenes
        with console.status("[cyan]Adding template scenes..."):
            with db.get_connection() as conn:
                cursor = conn.cursor()
                for scene in template['scenes']:
                    cursor.execute(
                        "INSERT INTO scenes (scene_number, title, description, characters) VALUES (?, ?, ?, ?)",
                        (scene['number'], scene['title'], scene['description'], scene['characters'])
                    )

        # Success tree
        tree = Tree("[bold green]Project Created from Template")
        tree.add(f"Location: {project_dir}")

        db_node = tree.add("Database Schema")
        db_node.add("projects [dim](1 row)[/dim]")
        db_node.add(f"characters [dim]({len(template['characters'])} rows)[/dim]")
        db_node.add(f"scenes [dim]({len(template['scenes'])} rows)[/dim]")
        db_node.add("brainstorm_sessions [dim](empty)[/dim]")
        db_node.add("drafts [dim](empty)[/dim]")

        content_node = tree.add("Template Content")
        content_node.add(f"Characters: {', '.join(c['name'] for c in template['characters'])}")
        content_node.add(f"Scenes: {len(template['scenes'])} starter scenes")

        console.print("\n")
        console.print(tree)

        return db_path

    def create_from_beat_sheet(
        self,
        name: str,
        genre: str = "Romantic Comedy"
    ) -> Path:
        """
        Create a new project from the universal 30-scene romcom beat sheet.

        Args:
            name: Project name (will be sanitized for filesystem)
            genre: Genre/type of screenplay

        Returns:
            Path to created database file

        Raises:
            ValueError: If project already exists

        Example:
            start = StartModule()
            db_path = start.create_from_beat_sheet(name="My Romcom")
        """
        beat_sheet = ROMCOM_BEAT_SHEET

        # Sanitize project name
        safe_name = self._sanitize_name(name)

        # Create project directory
        project_dir = self.projects_dir / safe_name
        if project_dir.exists():
            raise ValueError(f"Project '{name}' already exists at {project_dir}")

        project_dir.mkdir(parents=True, exist_ok=True)

        # Create database
        db_path = project_dir / f"{safe_name}.db"
        db = Database(db_path)

        # Welcome panel
        console.print(Panel.fit(
            f"[bold cyan]New Project with Beat Sheet[/bold cyan]\n\n"
            f"Project: {name}\n"
            f"Structure: {beat_sheet['name']}\n"
            f"Description: {beat_sheet['description']}",
            border_style="cyan"
        ))

        # Initialize schema and project
        with console.status("[cyan]Initializing database schema..."):
            db.initialize_schema()
            db.insert_project(
                name=name,
                genre=genre,
                description=beat_sheet['description']
            )

        # Populate characters
        with console.status("[cyan]Adding base characters..."):
            with db.get_connection() as conn:
                cursor = conn.cursor()
                for char in beat_sheet['characters']:
                    cursor.execute(
                        "INSERT INTO characters (name, description, role) VALUES (?, ?, ?)",
                        (char['name'], char['description'], char['role'])
                    )

        # Populate scenes
        with console.status("[cyan]Adding 30-scene structure..."):
            with db.get_connection() as conn:
                cursor = conn.cursor()
                for scene in beat_sheet['scenes']:
                    # Default characters for each scene
                    if scene['number'] <= 6:  # Act 1
                        chars = "Protagonist"
                    elif scene['number'] <= 15:  # Act 2A
                        chars = "Protagonist, Love Interest"
                    elif scene['number'] <= 24:  # Act 2B
                        chars = "Protagonist, Love Interest"
                    else:  # Act 3
                        chars = "Protagonist, Love Interest"

                    cursor.execute(
                        "INSERT INTO scenes (scene_number, title, description, characters) VALUES (?, ?, ?, ?)",
                        (scene['number'], scene['title'], scene['description'], chars)
                    )

        # Success tree showing act structure
        tree = Tree("[bold green]Project Created with Beat Sheet")
        tree.add(f"Location: {project_dir}")

        db_node = tree.add("Database Schema")
        db_node.add("projects [dim](1 row)[/dim]")
        db_node.add(f"characters [dim]({len(beat_sheet['characters'])} rows)[/dim]")
        db_node.add(f"scenes [dim]({len(beat_sheet['scenes'])} rows)[/dim]")
        db_node.add("writer_notes [dim](empty)[/dim]")
        db_node.add("brainstorm_sessions [dim](empty)[/dim]")
        db_node.add("drafts [dim](empty)[/dim]")

        structure_node = tree.add("Act Structure")
        act1_scenes = [s for s in beat_sheet['scenes'] if s.get('act') == 1]
        act2_scenes = [s for s in beat_sheet['scenes'] if s.get('act') == 2]
        act3_scenes = [s for s in beat_sheet['scenes'] if s.get('act') == 3]
        structure_node.add(f"Act 1: {len(act1_scenes)} scenes (pages 1-30)")
        structure_node.add(f"Act 2: {len(act2_scenes)} scenes (pages 30-90)")
        structure_node.add(f"Act 3: {len(act3_scenes)} scenes (pages 90-110)")

        console.print("\n")
        console.print(tree)

        return db_path

    def get_project_path(self, name: str) -> Optional[Path]:
        """
        Get database path for an existing project.

        Args:
            name: Project name

        Returns:
            Path to database file, or None if not found
        """
        safe_name = self._sanitize_name(name)
        db_path = self.projects_dir / safe_name / f"{safe_name}.db"

        if db_path.exists():
            return db_path
        return None

    def list_projects(self) -> list[str]:
        """
        List all existing projects.

        Returns:
            List of project names
        """
        if not self.projects_dir.exists():
            return []

        projects = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                # Look for .db file
                db_files = list(project_dir.glob("*.db"))
                if db_files:
                    # Get actual project name from database
                    db = Database(db_files[0])
                    project_data = db.get_project()
                    if project_data:
                        projects.append(project_data['name'])

        return projects

    def project_exists(self, name: str) -> bool:
        """
        Check if a project exists.

        Args:
            name: Project name

        Returns:
            True if project exists
        """
        return self.get_project_path(name) is not None

    @staticmethod
    def list_templates() -> Dict[str, dict]:
        """
        Get all available project templates (frameworks only).

        Returns:
            Dictionary of template_key: template_data
        """
        return TEMPLATES

    @staticmethod
    def list_preset_templates() -> Dict[str, dict]:
        """
        Get all available preset templates (specific examples).

        Returns:
            Dictionary of preset_key: preset_data
        """
        return PRESET_TEMPLATES

    @staticmethod
    def list_all_templates() -> Dict[str, dict]:
        """
        Get all templates - both frameworks and presets.

        Returns:
            Combined dictionary of all templates
        """
        return {**TEMPLATES, **PRESET_TEMPLATES}

    def delete_project(self, name: str) -> None:
        """
        Delete a project and its database.

        Args:
            name: Project name

        Raises:
            ValueError: If project doesn't exist
        """
        safe_name = self._sanitize_name(name)
        project_dir = self.projects_dir / safe_name

        if not project_dir.exists():
            raise ValueError(f"Project '{name}' not found")

        import shutil
        shutil.rmtree(project_dir)

    def get_project_metadata(self, name: str) -> Optional[dict]:
        """
        Get full project metadata.

        Args:
            name: Project name

        Returns:
            Project metadata dict or None
        """
        db_path = self.get_project_path(name)
        if not db_path:
            return None

        db = Database(db_path)
        project_data = db.get_project()

        if project_data:
            # Add counts
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM characters")
                project_data['character_count'] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM scenes")
                project_data['scene_count'] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM brainstorm_sessions")
                project_data['brainstorm_count'] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM drafts")
                project_data['draft_count'] = cursor.fetchone()[0]

        return project_data

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Sanitize project name for filesystem use.

        Args:
            name: Raw project name

        Returns:
            Safe filesystem name

        Example:
            "The Proposal 2.0!" -> "the_proposal_2_0"
        """
        # Convert to lowercase
        safe = name.lower()

        # Replace spaces and special chars with underscores
        safe = "".join(c if c.isalnum() else "_" for c in safe)

        # Remove consecutive underscores
        while "__" in safe:
            safe = safe.replace("__", "_")

        # Remove leading/trailing underscores
        safe = safe.strip("_")

        return safe


def _show_project_details(start: StartModule, project_name: str) -> None:
    """Display detailed project information."""
    metadata = start.get_project_metadata(project_name)

    if not metadata:
        console.print(f"[red]Error:[/red] Project '{project_name}' not found")
        return

    # Create details panel
    details = f"""[bold cyan]{metadata['name']}[/bold cyan]

Genre: {metadata['genre']}
Description: {metadata.get('description') or '(none)'}

Created: {metadata['created_at']}
Last Updated: {metadata['updated_at']}

Content:
  Characters: {metadata['character_count']}
  Scenes: {metadata['scene_count']}
  Brainstorm Sessions: {metadata['brainstorm_count']}
  Drafts: {metadata['draft_count']}
"""

    console.print(Panel(details, border_style="cyan", title="Project Details"))


def main():
    """
    Interactive CLI entrypoint for START module.

    Usage:
        python -m lizzy.start
    """
    import sys
    from rich.prompt import Prompt, Confirm
    from rich.table import Table

    console.print(Panel.fit(
        "[bold cyan]Lizzy Project Manager[/bold cyan]\n\n"
        "Manage your romantic comedy screenplay projects",
        border_style="cyan"
    ))

    start = StartModule()

    # Show existing projects
    existing = start.list_projects()

    if existing:
        table = Table(title="Existing Projects", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Project Name", style="green")
        table.add_column("Location")

        for idx, project_name in enumerate(existing, 1):
            safe_name = start._sanitize_name(project_name)
            location = f"projects/{safe_name}"
            table.add_row(str(idx), project_name, location)

        console.print("\n")
        console.print(table)
        console.print("\n")

    # Main menu
    console.print("[bold]What would you like to do?[/bold]")
    console.print("[1] Create new project")
    if existing:
        console.print("[2] Continue existing project")
        console.print("[3] View project details")
        console.print("[4] Delete project")
        console.print("[5] Exit")
        choices = ["1", "2", "3", "4", "5"]
    else:
        console.print("[2] Exit")
        choices = ["1", "2"]

    choice = Prompt.ask("Choose an option", choices=choices, default="1")

    # Exit
    if choice == "5" or (choice == "2" and not existing):
        console.print("\n[dim]Goodbye![/dim]")
        return

    # View project details
    if choice == "3" and existing:
        project_idx = int(Prompt.ask(
            "Choose project number",
            choices=[str(i) for i in range(1, len(existing) + 1)]
        ))
        project_name = existing[project_idx - 1]
        _show_project_details(start, project_name)
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
        main()  # Return to menu
        return

    # Delete project
    if choice == "4" and existing:
        project_idx = int(Prompt.ask(
            "Choose project number to delete",
            choices=[str(i) for i in range(1, len(existing) + 1)]
        ))
        project_name = existing[project_idx - 1]

        if Confirm.ask(f"[red]Delete project '{project_name}'? This cannot be undone.[/red]"):
            start.delete_project(project_name)
            console.print(f"\n[green]Project '{project_name}' deleted[/green]")
        else:
            console.print("\n[yellow]Cancelled[/yellow]")

        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
        main()  # Return to menu
        return

    # Continue existing
    if choice == "2" and existing:
        project_idx = int(Prompt.ask(
            "Choose project number",
            choices=[str(i) for i in range(1, len(existing) + 1)]
        ))
        project_name = existing[project_idx - 1]

        console.print(f"\n[green]Opening project:[/green] {project_name}")
        console.print(f"\n[cyan]Next step:[/cyan]")
        console.print(f"  python -m lizzy.intake \"{project_name}\"")
        return

    # Create new project
    console.print("\n[bold]How would you like to start?[/bold]")
    console.print("[1] Blank project")
    console.print("[2] Use 30-scene romcom beat sheet")

    create_choice = Prompt.ask("Choose an option", choices=["1", "2"], default="2")

    console.print("\n")
    name = Prompt.ask("[cyan]Project name[/cyan]")

    if create_choice == "2":
        # Use the universal beat sheet
        try:
            db_path = start.create_from_beat_sheet(name=name)

            console.print(f"\n[cyan]Next step:[/cyan]")
            console.print(f"  python -m lizzy.intake \"{name}\"")
            console.print(f"  [dim](Customize the 30 scenes to tell your specific story)[/dim]")

        except ValueError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]Unexpected error:[/red] {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        # Blank project
        genre = Prompt.ask("[cyan]Genre[/cyan]", default="Romantic Comedy")
        description = Prompt.ask("[cyan]Description (optional)[/cyan]", default="")

        try:
            db_path = start.create_project(
                name=name,
                genre=genre,
                description=description
            )

            console.print(f"\n[cyan]Next step:[/cyan]")
            console.print(f"  python -m lizzy.intake \"{name}\"")
            console.print(f"  [dim](Add characters and scenes to your project)[/dim]")

        except ValueError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]Unexpected error:[/red] {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
