"""
Typer callback validators.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from cli.console import console


def validate_csv(path: Path) -> Path:
    """Validate that CSV file exists."""
    if not path.exists():
        console.print(f"[error]CSV file not found: {path}[/]")
        raise typer.BadParameter(f"File not found: {path}")
    if not path.suffix == ".csv":
        console.print(f"[error]Not a CSV file: {path}[/]")
        raise typer.BadParameter(f"Not a CSV: {path}")
    return path


def validate_workers(value: int) -> int:
    """Validate worker count."""
    if value < 1:
        raise typer.BadParameter("Workers must be >= 1")
    if value > 32:
        console.print("[warning]Warning: >32 workers may cause rate limiting[/]")
    return value


def validate_priority(engines: Optional[List[str]]) -> Optional[List[str]]:
    """Validate search engine names."""
    if engines is None:
        return None
    valid = {"google", "duckduckgo", "bing"}
    for eng in engines:
        if eng not in valid:
            raise typer.BadParameter(
                f"Unknown engine: {eng}. Valid: {', '.join(valid)}"
            )
    return engines