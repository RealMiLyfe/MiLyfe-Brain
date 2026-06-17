"""MiLyfe Brain — Prompts System.

Provides hierarchical rule loading, slash commands, and output style management.
"""

from prompts.output_styles import OUTPUT_STYLES, get_style
from prompts.rule_loader import RuleLoader
from prompts.slash_commands import SLASH_COMMANDS, parse_slash_command

__all__ = [
    "RuleLoader",
    "SLASH_COMMANDS",
    "parse_slash_command",
    "OUTPUT_STYLES",
    "get_style",
]
