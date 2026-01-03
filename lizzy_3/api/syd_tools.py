"""
Syd's tools for editing the outline (SQLite) and querying knowledge buckets.
These get passed to the LLM for function calling.
"""

# =============================================================================
# BUCKET DEFINITIONS (for system prompt awareness)
# =============================================================================

AVAILABLE_BUCKETS = {
    "books-final": {
        "name": "Structure Expert",
        "description": "Screenwriting craft, structure, beats, character arcs, pacing, act breaks",
        "use_when": "Planning beats, pacing an act, fixing a sagging middle, designing character arcs, figuring out where the midpoint should hit",
        "asset": "Craft principles, structural frameworks"
    },
    "plays-final": {
        "name": "Dialogue Expert",
        "description": "Shakespeare's complete works - dialogue, dramatic patterns, subtext, conflict",
        "use_when": "Dialogue feels flat, need subtext, want banter that crackles, building emotional confrontation, character voice feels same-y",
        "asset": "Dramatic patterns, rhythm, conflict dynamics"
    },
    "scripts-final": {
        "name": "Execution Expert",
        "description": "Romcom screenplays - execution, visual storytelling, scene-setting, romantic comedy tone",
        "use_when": "Writing the actual scene, need visual comedy beats, setting up a meet-cute, landing a romantic moment, genre-specific tone check",
        "asset": "How romcoms actually do it on the page"
    }
}


def get_bucket_awareness_prompt() -> str:
    """Generate system prompt section for bucket awareness."""
    lines = ["You have access to three expert knowledge buckets. Know when to suggest them:\n"]

    for bucket_id, info in AVAILABLE_BUCKETS.items():
        lines.append(f"📚 {bucket_id} ({info['name']})")
        lines.append(f"   USE WHEN: {info['use_when']}")
        lines.append(f"   ASSET: {info['asset']}")
        lines.append("")

    lines.append("IMPORTANT: Before querying a bucket, ask the user first:")
    lines.append("  'I think [bucket] could help with [reason]. Want me to pull that in?'")
    lines.append("Only query after user confirms, OR if they manually activated it.")
    lines.append("When user activates a bucket, acknowledge it naturally.")

    return "\n".join(lines)


# =============================================================================
# BUCKET TOOLS
# =============================================================================

QUERY_BUCKET = {
    "type": "function",
    "function": {
        "name": "query_bucket",
        "description": "Query a knowledge bucket for domain expertise. Only use after user approves or manually activates the bucket.",
        "parameters": {
            "type": "object",
            "properties": {
                "bucket": {
                    "type": "string",
                    "enum": ["books-final", "plays-final", "scripts-final"],
                    "description": "Which bucket to query"
                },
                "query": {
                    "type": "string",
                    "description": "What to search for - be specific about the craft question"
                }
            },
            "required": ["bucket", "query"]
        }
    }
}

# =============================================================================
# PROJECT TOOLS
# =============================================================================

UPDATE_PROJECT = {
    "type": "function",
    "function": {
        "name": "update_project",
        "description": "Update project metadata (title, logline, genre, description). Use when user defines or refines core project info.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The screenplay title"
                },
                "logline": {
                    "type": "string",
                    "description": "One-sentence summary of the story (who, what, stakes)"
                },
                "genre": {
                    "type": "string",
                    "description": "Genre (usually 'Romantic Comedy')"
                },
                "description": {
                    "type": "string",
                    "description": "Longer description or notes about the project"
                }
            },
            "required": []
        }
    }
}

# =============================================================================
# WRITER NOTES TOOLS
# =============================================================================

UPDATE_NOTES = {
    "type": "function",
    "function": {
        "name": "update_notes",
        "description": "Update writer notes (theme, tone, comps, braindump). Use when user discusses tone, themes, or comparable films.",
        "parameters": {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "description": "Core theme(s) of the story (e.g., 'second chances', 'choosing authenticity over perfection')"
                },
                "tone": {
                    "type": "string",
                    "description": "Tonal description (e.g., 'witty, grounded, warm with sharp edges')"
                },
                "comps": {
                    "type": "string",
                    "description": "Comparable films or 'X meets Y' pitch (e.g., 'When Harry Met Sally meets The Proposal')"
                },
                "braindump": {
                    "type": "string",
                    "description": "Free-form notes, ideas, fragments the writer wants to remember"
                }
            },
            "required": []
        }
    }
}

# =============================================================================
# CHARACTER TOOLS
# =============================================================================

CREATE_CHARACTER = {
    "type": "function",
    "function": {
        "name": "create_character",
        "description": "Create a new character. Use when user introduces a new character for the first time.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Character name"
                },
                "role": {
                    "type": "string",
                    "description": "Role in story (protagonist, love interest, best friend, antagonist, mentor, etc.)"
                },
                "description": {
                    "type": "string",
                    "description": "Brief character description (job, situation, key traits)"
                },
                "arc": {
                    "type": "string",
                    "description": "Character arc - what they learn or how they change"
                },
                "age": {
                    "type": "string",
                    "description": "Age or age range"
                },
                "personality": {
                    "type": "string",
                    "description": "Personality traits, quirks, mannerisms"
                },
                "flaw": {
                    "type": "string",
                    "description": "Core flaw or wound that drives their arc"
                },
                "backstory": {
                    "type": "string",
                    "description": "Relevant backstory"
                },
                "relationships": {
                    "type": "string",
                    "description": "Key relationships to other characters"
                }
            },
            "required": ["name"]
        }
    }
}

UPDATE_CHARACTER = {
    "type": "function",
    "function": {
        "name": "update_character",
        "description": "Update an existing character. Use when user adds details or changes something about a character.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "ID of the character to update"
                },
                "name": {
                    "type": "string",
                    "description": "Character name"
                },
                "role": {
                    "type": "string",
                    "description": "Role in story"
                },
                "description": {
                    "type": "string",
                    "description": "Brief character description"
                },
                "arc": {
                    "type": "string",
                    "description": "Character arc"
                },
                "age": {
                    "type": "string",
                    "description": "Age or age range"
                },
                "personality": {
                    "type": "string",
                    "description": "Personality traits"
                },
                "flaw": {
                    "type": "string",
                    "description": "Core flaw"
                },
                "backstory": {
                    "type": "string",
                    "description": "Backstory"
                },
                "relationships": {
                    "type": "string",
                    "description": "Relationships"
                }
            },
            "required": ["character_id"]
        }
    }
}

DELETE_CHARACTER = {
    "type": "function",
    "function": {
        "name": "delete_character",
        "description": "Delete a character. Use when user explicitly says to remove a character.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "ID of the character to delete"
                }
            },
            "required": ["character_id"]
        }
    }
}

# =============================================================================
# SCENE TOOLS
# =============================================================================

CREATE_SCENE = {
    "type": "function",
    "function": {
        "name": "create_scene",
        "description": "Create a new scene. Use when user defines a new scene or beat.",
        "parameters": {
            "type": "object",
            "properties": {
                "scene_number": {
                    "type": "integer",
                    "description": "Scene number (1-30 typically for romcom structure)"
                },
                "title": {
                    "type": "string",
                    "description": "Scene title (e.g., 'Meet Cute', 'First Kiss', 'Dark Night of the Soul')"
                },
                "description": {
                    "type": "string",
                    "description": "What happens in the scene"
                },
                "characters": {
                    "type": "string",
                    "description": "Characters present in the scene (comma-separated)"
                },
                "tone": {
                    "type": "string",
                    "description": "Tone of the scene (e.g., 'comedic', 'romantic', 'tense')"
                },
                "beats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key beats or moments within the scene"
                }
            },
            "required": ["scene_number"]
        }
    }
}

UPDATE_SCENE = {
    "type": "function",
    "function": {
        "name": "update_scene",
        "description": "Update an existing scene. Use when user refines or changes scene details.",
        "parameters": {
            "type": "object",
            "properties": {
                "scene_id": {
                    "type": "integer",
                    "description": "ID of the scene to update"
                },
                "scene_number": {
                    "type": "integer",
                    "description": "Scene number"
                },
                "title": {
                    "type": "string",
                    "description": "Scene title"
                },
                "description": {
                    "type": "string",
                    "description": "What happens"
                },
                "characters": {
                    "type": "string",
                    "description": "Characters present"
                },
                "tone": {
                    "type": "string",
                    "description": "Scene tone"
                },
                "beats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key beats"
                }
            },
            "required": ["scene_id"]
        }
    }
}

DELETE_SCENE = {
    "type": "function",
    "function": {
        "name": "delete_scene",
        "description": "Delete a scene. Use when user explicitly says to remove a scene.",
        "parameters": {
            "type": "object",
            "properties": {
                "scene_id": {
                    "type": "integer",
                    "description": "ID of the scene to delete"
                }
            },
            "required": ["scene_id"]
        }
    }
}

WRITE_SCENE = {
    "type": "function",
    "function": {
        "name": "write_scene",
        "description": "Write formatted screenplay content for a scene. Use when user asks you to write, draft, or flesh out an actual scene. This writes to the Canvas.",
        "parameters": {
            "type": "object",
            "properties": {
                "scene_id": {
                    "type": "integer",
                    "description": "ID of the scene to write"
                },
                "elements": {
                    "type": "array",
                    "description": "Array of screenplay elements in order. Each element has 'type' and 'text'.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["scene-heading", "action", "character", "dialogue", "parenthetical", "transition"],
                                "description": "Element type: scene-heading (INT./EXT. LOCATION - TIME), action (description), character (CHARACTER NAME in caps), dialogue (what they say), parenthetical (how they say it), transition (CUT TO:, FADE OUT, etc.)"
                            },
                            "text": {
                                "type": "string",
                                "description": "The content of this element"
                            }
                        },
                        "required": ["type", "text"]
                    }
                }
            },
            "required": ["scene_id", "elements"]
        }
    }
}

# =============================================================================
# ALL TOOLS
# =============================================================================

SYD_TOOLS = [
    # Bucket tools
    QUERY_BUCKET,
    # Outline tools
    UPDATE_PROJECT,
    UPDATE_NOTES,
    CREATE_CHARACTER,
    UPDATE_CHARACTER,
    DELETE_CHARACTER,
    CREATE_SCENE,
    UPDATE_SCENE,
    DELETE_SCENE,
    WRITE_SCENE,
]


def get_tool_names() -> list[str]:
    """Get list of all tool names."""
    return [tool["function"]["name"] for tool in SYD_TOOLS]
