"""
Static blocks for Prompt Studio

These blocks add static text, templates, and formatting.
"""

from typing import Optional
from .base import Block


class TextBlock(Block):
    """
    Simple text block - outputs static text.

    Useful for instructions, separators, or fixed prompts.
    """

    def __init__(self, text: str, block_id: str = None):
        super().__init__(block_id)
        self.text = text

    def execute(self, project_name: str, **kwargs) -> str:
        return self.text

    def get_description(self) -> str:
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Text: '{preview}'"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.text is None:
            return (False, "Text cannot be None")
        return (True, None)


class TemplateBlock(Block):
    """
    Template block with variable substitution.

    Uses simple {variable} syntax for replacement.
    """

    def __init__(self, template: str, variables: dict = None, block_id: str = None):
        super().__init__(block_id)
        self.template = template
        self.variables = variables or {}

    def execute(self, project_name: str, **kwargs) -> str:
        # Merge kwargs with stored variables (kwargs takes precedence)
        all_vars = {**self.variables, **kwargs}
        all_vars['project_name'] = project_name

        try:
            return self.template.format(**all_vars)
        except KeyError as e:
            return f"[Template error: Missing variable {e}]"

    def get_description(self) -> str:
        preview = self.template[:50] + "..." if len(self.template) > 50 else self.template
        return f"Template: '{preview}' (vars: {list(self.variables.keys())})"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.template is None:
            return (False, "Template cannot be None")
        return (True, None)


class SectionHeaderBlock(Block):
    """
    Formatted section header block.

    Creates a visually distinct section header with dividers.
    """

    def __init__(self, title: str, divider_char: str = "=", width: int = 80, block_id: str = None):
        super().__init__(block_id)
        self.title = title
        self.divider_char = divider_char
        self.width = width

    def execute(self, project_name: str, **kwargs) -> str:
        divider = self.divider_char * self.width
        return f"\n{divider}\n{self.title.center(self.width)}\n{divider}\n"

    def get_description(self) -> str:
        return f"Section header: '{self.title}'"

    def validate(self) -> tuple[bool, Optional[str]]:
        if not self.title:
            return (False, "Title cannot be empty")
        if len(self.divider_char) != 1:
            return (False, "Divider must be a single character")
        return (True, None)
