"""
Rich display components — banners, tables, progress, panels.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from cli.console import console


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BANNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BANNER = r"""
     _         _                  ___   ___   ___  
    / \       | |                / _ \ / _ \ / _ \ 
   / _ \   _  | |  _____ _____  | | | | | | | | | |
  / ___ \ | |_| | |_____|_____| | |_| | |_| | |_| |
 /_/   \_(_)___/                 \___/ \___/ \___/ 
                                                   
"""


def show_banner() -> None:
    """Display the startup banner."""
    panel = Panel(
        Align.center(Text(BANNER, style="bold cyan")),
        border_style="bright_blue",
        padding=(0, 2),
    )
    console.print(panel)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG TABLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_config_table(config: Dict[str, Any]) -> None:
    """Display configuration as a rich table."""
    table = Table(
        title="⚙️  Configuration",
        box=box.ROUNDED,
        border_style="bright_blue",
        show_header=True,
        header_style="bold white on blue",
        padding=(0, 1),
    )
    table.add_column("Setting", style="stat_key", min_width=20)
    table.add_column("Value", style="stat_val", min_width=30)

    for key, value in config.items():
        # Color code booleans
        if isinstance(value, bool):
            val_str = "✅ Yes" if value else "❌ No"
            style = "success" if value else "muted"
        elif isinstance(value, list):
            val_str = " → ".join(str(v) for v in value)
            style = "engine"
        elif isinstance(value, (int, float)):
            val_str = str(value)
            style = "highlight"
        else:
            val_str = str(value)
            style = "stat_val"

        table.add_row(key, Text(val_str, style=style))

    console.print(table)
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VERIFICATION STATUS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_verification_status(status: Dict[str, Any]) -> None:
    """Show CLIP/BLIP model status panel."""
    tree = Tree("🔍 Verification Models", style="bold")

    clip_status = "✅ Loaded" if status.get("clip_loaded") else "❌ Not loaded"
    blip_status = "✅ Loaded" if status.get("blip_loaded") else "❌ Not loaded"

    clip_branch = tree.add(f"CLIP: {clip_status}")
    if status.get("clip_loaded"):
        clip_branch.add(f"Model: {status.get('clip_model', 'unknown')}")

    blip_branch = tree.add(f"BLIP: {blip_status}")
    if status.get("blip_loaded"):
        blip_branch.add(f"Model: {status.get('blip_model', 'unknown')}")

    tree.add(f"Device: {status.get('device', 'cpu')}")
    tree.add(f"Models dir: {status.get('models_dir', 'default')}")

    panel = Panel(tree, border_style="green" if any([
        status.get("clip_loaded"), status.get("blip_loaded")
    ]) else "yellow")

    console.print(panel)
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CSV INFO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_csv_info(total_rows: int, columns: List[str], skip: int = 0) -> None:
    """Show CSV file information."""
    table = Table(
        title="📄 Input CSV",
        box=box.SIMPLE_HEAVY,
        border_style="bright_blue",
    )
    table.add_column("Metric", style="stat_key")
    table.add_column("Value", style="stat_val")

    table.add_row("Total rows", str(total_rows))
    table.add_row("To process", str(total_rows - skip))
    table.add_row("Already done", str(skip))
    table.add_row("Columns", ", ".join(columns[:8]) + ("..." if len(columns) > 8 else ""))

    console.print(table)
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROGRESS BAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_progress() -> Progress:
    """Create a rich progress bar for the pipeline."""
    return Progress(
        SpinnerColumn("dots", style="progress"),
        TextColumn("[progress]{task.description}[/]"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bright_green"),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn("│"),
        TimeElapsedColumn(),
        TextColumn("│"),
        TimeRemainingColumn(),
        console=console,
        expand=False,
    )


def create_search_progress() -> Progress:
    """Progress bar for search operations."""
    return Progress(
        SpinnerColumn("earth", style="engine"),
        TextColumn("[engine]{task.description}[/]"),
        BarColumn(bar_width=20, complete_style="cyan"),
        MofNCompleteColumn(),
        console=console,
        transient=True,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FINAL REPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# def show_final_report(stats: Dict[str, Any]) -> None:
#     """Display the final pipeline statistics."""
#     table = Table(
#         title="📊 Pipeline Report",
#         box=box.DOUBLE_EDGE,
#         border_style="bright_green",
#         show_header=True,
#         header_style="bold white on green",
#     )
#     table.add_column("Metric", style="stat_key", min_width=18)
#     table.add_column("Count", justify="right", style="stat_val", min_width=8)
#     table.add_column("", min_width=10)

#     total = stats.get("total", 0)
#     success = stats.get("success", 0)
#     rate = (success / total * 100) if total > 0 else 0

#     rows = [
#         ("✅ Success", success, f"[green]{rate:.1f}%[/]"),
#         ("❌ Failed", stats.get("failed", 0), ""),
#         ("🖼️  Placeholders", stats.get("placeholder", 0), ""),
#         ("🎭 BG Removed", stats.get("bg_removed", 0), ""),
#         ("⏭️  BG Skipped", stats.get("bg_skipped", 0), ""),
#         ("💾 Cache Hits", stats.get("cache_hits", 0), ""),
#         ("🔍 Verified", stats.get("verified", 0), ""),
#         ("🚫 Verify Rejects", stats.get("verify_fails", 0), ""),
#         ("🔄 DLQ Retries", stats.get("dlq_retries", 0), ""),
#         ("⏩ Skipped", stats.get("skipped", 0), ""),
#     ]

#     for label, count, extra in rows:
#         table.add_row(label, str(count), extra)

#     table.add_section()

#     elapsed = stats.get("elapsed", 0)
#     throughput = total / max(elapsed, 0.1)
#     table.add_row("⏱️  Elapsed", f"{elapsed:.1f}s", "")
#     table.add_row("🚀 Throughput", f"{throughput:.2f}", "ads/sec")
#     table.add_row("📦 Total", str(total), "")

#     console.print()
#     console.print(table)
#     console.print()

def show_final_report(stats: Dict[str, Any]) -> None:
    table = Table(
        title="📊 Pipeline Report",
        box=box.DOUBLE_EDGE,
        border_style="bright_green",
        show_header=True,
        header_style="bold white on green",
    )
    table.add_column("Metric", style="stat_key", min_width=22)
    table.add_column("Count", justify="right", style="stat_val", min_width=8)
    table.add_column("", min_width=10)

    total = stats.get("total", 0)
    success = stats.get("success", 0)
    rate = (success / total * 100) if total > 0 else 0

    rows = [
        ("✅ Success",           success,                           f"[green]{rate:.1f}%[/]"),
        ("❌ Failed",            stats.get("failed", 0),            ""),
        ("🖼️  Placeholders",     stats.get("placeholder", 0),       ""),
        ("🎭 BG Removed",        stats.get("bg_removed", 0),        ""),
        ("⏭️  BG Skipped",       stats.get("bg_skipped", 0),        ""),
        ("💾 Cache Hits",         stats.get("cache_hits", 0),        ""),
    ]

    for label, count, extra in rows:
        table.add_row(label, str(count), extra)

    # Verification section
    table.add_section()

    v1_total = stats.get("verified", 0)
    v1_fail  = stats.get("verify_fails", 0)
    v2_total = stats.get("post_verified", 0)
    v2_fail  = stats.get("post_verify_fails", 0)
    recomp   = stats.get("recomposed", 0)

    table.add_row(
        "🔍 Stage 1 (Download)",
        str(v1_total),
        f"[red]{v1_fail} rejected[/]" if v1_fail else "[green]all passed[/]",
    )
    table.add_row(
        "🔍 Stage 2 (Compose)",
        str(v2_total),
        f"[red]{v2_fail} rejected[/]" if v2_fail else "[green]all passed[/]",
    )
    table.add_row(
        "🔄 Recomposed",
        str(recomp),
        "[yellow]recovery attempts[/]" if recomp else "",
    )

    table.add_section()

    elapsed = stats.get("elapsed", 0)
    throughput = total / max(elapsed, 0.1)
    table.add_row("⏱️  Elapsed",    f"{elapsed:.1f}s", "")
    table.add_row("🚀 Throughput",   f"{throughput:.2f}", "ads/sec")
    table.add_row("📦 Total",        str(total), "")

    console.print()
    console.print(table)
    console.print()


# ━━━━━━━━���━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENGINE HEALTH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_engine_health(health_data: Dict[str, Dict]) -> None:
    """Show search engine health table."""
    if not health_data:
        return

    table = Table(
        title="🏥 Search Engine Health",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("Engine", style="engine")
    table.add_column("Calls", justify="right")
    table.add_column("Success", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("Avg Results", justify="right")
    table.add_column("Failures", justify="right")

    for name, data in health_data.items():
        sr = data.get("success_rate", "0%")
        style = "green" if "100" in sr or "9" in sr[:2] else "yellow"
        table.add_row(
            name,
            str(data.get("calls", 0)),
            Text(sr, style=style),
            data.get("avg_latency", "0s"),
            data.get("avg_results", "0"),
            str(data.get("failures", 0)),
        )

    console.print(table)
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ROW STATUS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def format_row_status(
    idx: int,
    total: int,
    query: str,
    status: str = "processing",
    extra: str = "",
) -> str:
    """Format a single row status line for the progress bar."""
    if status == "success":
        icon = "✅"
    elif status == "failed":
        icon = "❌"
    elif status == "cached":
        icon = "💾"
    elif status == "verified":
        icon = "🔍"
    else:
        icon = "🔄"

    return f"{icon} [{idx}/{total}] {query[:40]}{' — ' + extra if extra else ''}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GOODBYE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_goodbye(output_path: str, interrupted: bool = False) -> None:
    """Show exit message."""
    if interrupted:
        panel = Panel(
            Align.center(Text(
                "⚠️  Interrupted — progress saved!\n"
                f"Resume by running again with --resume\n"
                f"Output: {output_path}",
                style="warning",
            )),
            border_style="yellow",
            title="Paused",
        )
    else:
        panel = Panel(
            Align.center(Text(
                f"✅ All done!\n"
                f"Output: {output_path}",
                style="success",
            )),
            border_style="green",
            title="Complete",
        )

    console.print(panel)