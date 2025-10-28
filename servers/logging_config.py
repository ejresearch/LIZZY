"""
Logging configuration for LIZZY servers.

Re-exports the main lizzy.logging_config for server use.
"""

from pathlib import Path
import sys

# Add parent directory to path to import lizzy (only if not already importable)
try:
    from lizzy.logging_config import get_logger, LizzyLogger, set_debug_mode
except ImportError:
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    from lizzy.logging_config import get_logger, LizzyLogger, set_debug_mode

# Re-export for convenience
__all__ = ['get_logger', 'LizzyLogger', 'set_debug_mode']
