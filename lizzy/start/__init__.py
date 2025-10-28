"""
START Module - Project Initialization

Organized sub-modules for templates and project creation.
"""

import sys
from pathlib import Path

# Import from templates submodule
from .templates import ROMCOM_BEAT_SHEET, get_templates, get_template

# Import StartModule from parent start.py file
# We need to import from lizzy.start module (the .py file, not this directory)
# Python imported this __init__.py as lizzy.start, so we need to go up and import the .py
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import the actual start.py module as start_module to avoid circular import
import importlib.util
start_py_path = Path(__file__).parent.parent / 'start.py'
spec = importlib.util.spec_from_file_location("lizzy.start_module", start_py_path)
start_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start_module)

# Get StartModule class from the start.py file
StartModule = start_module.StartModule

__all__ = [
    'ROMCOM_BEAT_SHEET',
    'get_templates',
    'get_template',
    'StartModule'
]
