#!/usr/bin/env python3
"""
Quick access to Automated Brainstorm.

Batch process all 30 scenes with expert consultation from
books, plays, and scripts buckets.

Usage:
    python3 autobrainstorm.py
"""

if __name__ == "__main__":
    import asyncio
    from lizzy.automated_brainstorm import main
    asyncio.run(main())
