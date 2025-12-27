"""
START Module - Templates for project initialization.

Note: StartModule has been merged into project_creator.py.
Use backend.project_creator instead.
"""

# Import from templates submodule
from .templates import ROMCOM_BEAT_SHEET, get_templates, get_template

__all__ = [
    'ROMCOM_BEAT_SHEET',
    'get_templates',
    'get_template',
]
