"""
Rich console singleton — used everywhere for styled output.
"""

from rich.console import Console
from rich.theme import Theme

# Custom theme for the project
THEME = Theme({
    "info":      "cyan",
    "success":   "bold green",
    "warning":   "bold yellow",
    "error":     "bold red",
    "highlight": "bold magenta",
    "muted":     "dim white",
    "header":    "bold white on blue",
    "engine":    "bold cyan",
    "query":     "italic yellow",
    "score":     "bold green",
    "score_bad": "bold red",
    "progress":  "bold blue",
    "stat_key":  "bold white",
    "stat_val":  "cyan",
})

console = Console(theme=THEME)