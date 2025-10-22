#!/usr/bin/env python3
"""
Quick access to Interactive Brainstorm.

Usage:
    python3 brainstorm.py              # Select project interactively
    python3 brainstorm.py "My Project" # Launch directly
"""

if __name__ == "__main__":
    import asyncio
    from lizzy.interactive_brainstorm import main
    asyncio.run(main())
