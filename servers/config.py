"""
Server Configuration for LIZZY API

Re-exports the main lizzy.config for server use.
This allows servers to import from a local config module.
"""

from pathlib import Path
import sys

# Add parent directory to path to import lizzy
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from lizzy.config import config, LizzyConfig

# Re-export for convenience
__all__ = ['config', 'LizzyConfig']
