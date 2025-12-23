"""
Project Templates for START Module

Contains beat sheets and character templates for different story types.
"""

from typing import Dict


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


def get_templates() -> Dict[str, Dict]:
    """
    Get all available project templates.

    Returns:
        Dictionary of template definitions
    """
    return {
        "romcom_beat_sheet": ROMCOM_BEAT_SHEET
    }


def get_template(template_name: str) -> Dict:
    """
    Get a specific template by name.

    Args:
        template_name: Name of the template

    Returns:
        Template dictionary

    Raises:
        KeyError: If template doesn't exist
    """
    templates = get_templates()
    return templates[template_name]
