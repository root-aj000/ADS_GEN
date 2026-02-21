"""
Typer CLI application with Rich integration.

Commands:
    run       — Main pipeline (generate ads)
    status    — Show progress status
    config    — Show current configuration
    cache     — Cache management (stats, clear)
    verify    — Test verification on a single image
    clean     — Clean temp files
"""

from __future__ import annotations

import sys
import time
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer
from rich.prompt import Confirm, IntPrompt, Prompt

from cli.console import console
from cli.display import (
    show_banner,
    show_config_table,
    show_csv_info,
    show_engine_health,
    show_final_report,
    show_goodbye,
    show_verification_status,
)

app = typer.Typer(
    name="adgen",
    help="🚀 Ad Generator v4.0 — Production-grade ad image pipeline",
    rich_markup_mode="rich",
    add_completion=True,
    no_args_is_help=False,
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENUMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SearchEngine(str, Enum):
    google     = "google"
    duckduckgo = "duckduckgo"
    bing       = "bing"


class LogLevel(str, Enum):
    debug   = "debug"
    info    = "info"
    warning = "warning"
    error   = "error"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RUN COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def run(
    # ── Core settings ──
    resume: bool = typer.Option(
        True,
        "--resume/--fresh",
        "-r/-f",
        help="Resume from progress or start fresh",
    ),
    workers: int = typer.Option(
        4,
        "--workers", "-w",
        help="Number of concurrent threads",
        min=1, max=32,
    ),
    
    # ── Range ──
    start: Optional[int] = typer.Option(
        None,
        "--start", "-s",
        help="Start index (0-based)",
    ),
    end: Optional[int] = typer.Option(
        None,
        "--end", "-e",
        help="End index (exclusive)",
    ),
    chunk: int = typer.Option(
        50,
        "--chunk", "-c",
        help="Chunk size for batch processing",
        min=1,
    ),
    
    # ── Search ──
    priority: Optional[List[SearchEngine]] = typer.Option(
        None,
        "--priority", "-p",
        help="Search engine priority order",
    ),
    
    # ── Features ──
    verify: bool = typer.Option(
        True,
        "--verify/--no-verify",
        help="Enable CLIP+BLIP image verification",
    ),
    cache: bool = typer.Option(
        True,
        "--cache/--no-cache",
        help="Enable image download cache",
    ),
    bg_remove: bool = typer.Option(
        True,
        "--bg/--no-bg",
        help="Enable background removal",
    ),
    
    # ── Output ──
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Search & download only, skip compositing",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable debug logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Minimal output (errors only)",
    ),
    
    # ── Paths ──
    input_csv: Optional[Path] = typer.Option(
        None,
        "--input", "-i",
        help="Input CSV file path",
        exists=True,
        dir_okay=False,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output images directory",
    ),
) -> None:
    """
    🚀 [bold]Generate ad images[/bold] from CSV data.

    Downloads product images, removes backgrounds, and composes
    professional ad images with text overlays.

    [dim]Examples:[/dim]
        adgen run
        adgen run --fresh --workers 8
        adgen run --priority google bing --no-verify
        adgen run --start 100 --end 200 --verbose
        adgen run --input data/custom.csv --output output/
    """
    from config.settings import cfg, AppConfig
    from utils.log_config import setup_root

    # Show banner
    if not quiet:
        show_banner()

    # ── Apply CLI overrides to config ──
    cfg.resume = resume
    cfg.dry_run = dry_run
    cfg.verbose = verbose
    cfg.start_index = start
    cfg.end_index = end
    cfg.chunk_size = chunk
    cfg.pipeline = cfg.pipeline.__class__(
        max_workers=workers,
        inter_ad_delay=cfg.pipeline.inter_ad_delay,
        csv_save_interval=cfg.pipeline.csv_save_interval,
        download_timeout=cfg.pipeline.download_timeout,
        worker_timeout=cfg.pipeline.worker_timeout,
    )
    cfg.enable_cache = cache

    # Override paths if provided
    if input_csv:
        cfg.paths = cfg.paths.__class__(
            **{**{f.name: getattr(cfg.paths, f.name) for f in cfg.paths.__dataclass_fields__.values()},
               "csv_input": input_csv}
        )
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        cfg.paths = cfg.paths.__class__(
            **{**{f.name: getattr(cfg.paths, f.name) for f in cfg.paths.__dataclass_fields__.values()},
               "images_dir": output_dir}
        )

    # Override verification
    if not verify:
        cfg.verify = cfg.verify.__class__(
            **{**{f.name: getattr(cfg.verify, f.name) for f in cfg.verify.__dataclass_fields__.values()},
               "use_clip": False, "use_blip": False}
        )

    # Override priority
    if priority:
        engine_list = [e.value for e in priority]
        cfg.search = cfg.search.__class__(
            **{**{f.name: getattr(cfg.search, f.name) for f in cfg.search.__dataclass_fields__.values()},
               "priority": engine_list}
        )

    # ── Setup logging ──
    log_level = "debug" if verbose else ("warning" if quiet else "info")
    setup_root(cfg.paths.log_file, verbose=verbose)

    # ── Show config ──
    if not quiet:
        show_config_table({
            "Workers": workers,
            "Resume": resume,
            "Dry Run": dry_run,
            "Verification": verify,
            "Cache": cache,
            "BG Removal": bg_remove,
            "Search Priority": cfg.search.priority,
            "Chunk Size": chunk,
            "Start Index": start or "beginning",
            "End Index": end or "end",
            "Input CSV": str(cfg.paths.csv_input),
            "Output Dir": str(cfg.paths.images_dir),
        })

    # ── Validate ──
    cfg.paths.ensure()
    cfg.validate()

    # ── Build pipeline ──
    from core.pipeline import AdPipeline
    pipeline = AdPipeline(cfg)

    if not resume:
        pipeline.progress.reset()
        if not quiet:
            console.print("[warning]Progress reset — starting fresh[/]")

    # ── Show CSV info ──
    if not quiet:
        total = len(pipeline.df)
        done = pipeline.progress.completed_count
        show_csv_info(total, list(pipeline.df.columns), skip=done)

    # ── Show verification ──
    if not quiet and pipeline.verifier:
        show_verification_status(pipeline.verifier.stats())

    # ── Confirm if large dataset ──
    total_to_process = len(pipeline.df) - pipeline.progress.completed_count
    if not quiet and total_to_process > 500:
        if not Confirm.ask(
            f"[warning]Process {total_to_process} rows? This may take a while[/]",
            default=True,
        ):
            console.print("[muted]Cancelled[/]")
            raise typer.Exit()

    # ── Run ──
    if not quiet:
        console.print()
        console.rule("[progress]Starting Pipeline[/]", style="bright_blue")
        console.print()

    try:
        pipeline.run()
    except KeyboardInterrupt:
        console.print()

    # ── Final report ──
    if not quiet:
        stats_dict = {
            "total": pipeline.stats.total.value,
            "success": pipeline.stats.success.value,
            "failed": pipeline.stats.failed.value,
            "placeholder": pipeline.stats.placeholder.value,
            "bg_removed": pipeline.stats.bg_removed.value,
            "bg_skipped": pipeline.stats.bg_skipped.value,
            "cache_hits": pipeline.stats.cache_hits.value,
            "verified": pipeline.stats.verified.value,
            "verify_fails": pipeline.stats.verify_fails.value,
            "dlq_retries": pipeline.stats.dlq_retries.value,
            "skipped": pipeline.stats.skipped.value,
            "elapsed": pipeline.stats.elapsed,
        }
        show_final_report(stats_dict)

        if pipeline.health:
            show_engine_health(pipeline.health.get_report())

        interrupted = pipeline._shutdown.should_stop if hasattr(pipeline, '_shutdown') else False
        show_goodbye(str(cfg.paths.csv_output), interrupted=interrupted)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATUS COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def status() -> None:
    """
    📊 Show current pipeline progress and statistics.
    """
    from config.settings import cfg
    from core.progress import ProgressManager

    show_banner()

    cfg.paths.ensure()

    if not cfg.paths.progress_db.exists():
        console.print("[warning]No progress data found. Run 'adgen run' first.[/]")
        raise typer.Exit()

    pm = ProgressManager(cfg.paths.progress_db)
    stats = pm.stats()

    table = Table(
        title="📊 Progress Status",
        box=box.ROUNDED,
        border_style="bright_blue",
    )
    table.add_column("Status", style="stat_key")
    table.add_column("Count", justify="right", style="stat_val")

    for status_name, count in stats.items():
        icon = {"done": "✅", "failed": "❌", "pending": "⏳"}.get(status_name, "❔")
        table.add_row(f"{icon} {status_name.title()}", str(count))

    total = sum(stats.values())
    done = stats.get("done", 0)
    pct = (done / total * 100) if total > 0 else 0

    table.add_section()
    table.add_row("📦 Total", str(total))
    table.add_row("📈 Progress", f"{pct:.1f}%")

    console.print(table)

    # Dead letter queue
    dlq = pm.get_dead_letters()
    if dlq:
        console.print(f"\n[warning]⚠️  {len(dlq)} rows in dead-letter queue (will retry)[/]")

    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def config() -> None:
    """
    ⚙️  Show current configuration from settings.py.
    """
    from config.settings import cfg

    show_banner()

    show_config_table({
        "Input CSV": str(cfg.paths.csv_input),
        "Output CSV": str(cfg.paths.csv_output),
        "Images Dir": str(cfg.paths.images_dir),
        "Models Dir": str(cfg.paths.models_dir),
        "Resume": cfg.resume,
        "Dry Run": cfg.dry_run,
        "Verbose": cfg.verbose,
        "Workers": cfg.pipeline.max_workers,
        "Chunk Size": cfg.chunk_size,
        "Search Priority": cfg.search.priority,
        "CLIP Verify": cfg.verify.use_clip,
        "BLIP Verify": cfg.verify.use_blip,
        "CLIP Model": cfg.verify.clip_model,
        "BLIP Model": cfg.verify.blip_model,
        "Image Cache": cfg.enable_cache,
        "Dead Letter Q": cfg.enable_dlq,
        "Health Monitor": cfg.enable_health,
        "Download Timeout": f"{cfg.pipeline.download_timeout}s",
        "Worker Timeout": f"{cfg.pipeline.worker_timeout}s",
    })

    # Check file existence
    checks = [
        ("Input CSV", cfg.paths.csv_input),
        ("Progress DB", cfg.paths.progress_db),
        ("Cache DB", cfg.paths.cache_db),
        ("Models Dir", cfg.paths.models_dir),
    ]

    table = Table(title="📁 File Status", box=box.SIMPLE)
    table.add_column("File")
    table.add_column("Status")
    table.add_column("Path", style="muted")

    for name, path in checks:
        exists = path.exists()
        status_str = "✅ Found" if exists else "❌ Missing"
        style = "green" if exists else "red"
        table.add_row(name, Text(status_str, style=style), str(path))

    console.print(table)
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CACHE COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def cache_cmd(
    clear: bool = typer.Option(False, "--clear", help="Clear the image cache"),
    stats: bool = typer.Option(True, "--stats/--no-stats", help="Show cache stats"),
) -> None:
    """
    💾 Manage the image download cache.
    """
    from config.settings import cfg
    from imaging.cache import ImageCache

    show_banner()

    cfg.paths.ensure()

    if not cfg.paths.cache_db.exists():
        console.print("[warning]No cache database found.[/]")
        raise typer.Exit()

    ic = ImageCache(cfg.paths.cache_db)

    if stats:
        cache_stats = ic.stats()
        table = Table(title="💾 Cache Statistics", box=box.ROUNDED, border_style="cyan")
        table.add_column("Metric", style="stat_key")
        table.add_column("Value", style="stat_val")

        total = cache_stats.get("total", 0)
        hits = cache_stats.get("total_hits", 0)
        size_bytes = cache_stats.get("total_bytes", 0)
        size_mb = (size_bytes or 0) / (1024 * 1024)

        table.add_row("Cached queries", str(total))
        table.add_row("Total hits", str(hits))
        table.add_row("Cache size", f"{size_mb:.1f} MB")

        console.print(table)

    if clear:
        if Confirm.ask("[warning]Clear the entire cache?[/]", default=False):
            ic.clear()
            console.print("[success]Cache cleared![/]")
        else:
            console.print("[muted]Cancelled[/]")

    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VERIFY COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def verify(
    image_path: Path = typer.Argument(..., help="Path to image file", exists=True),
    query: str = typer.Argument(..., help="Text query to verify against"),
) -> None:
    """
    🔍 Test CLIP+BLIP verification on a single image.

    [dim]Example: adgen verify photo.jpg "red nike shoes"[/dim]
    """
    from PIL import Image as PILImage
    from config.settings import cfg
    from imaging.verifier import ImageVerifier

    show_banner()

    console.print(f"[info]Image:[/] {image_path}")
    console.print(f"[info]Query:[/] {query}")
    console.print()

    cfg.paths.ensure()

    with console.status("Loading models...", spinner="dots"):
        verifier = ImageVerifier(cfg.verify, models_dir=cfg.paths.models_dir)

    if not verifier.is_available:
        console.print("[error]No verification models loaded![/]")
        console.print("[muted]Install: pip install transformers torch[/]")
        raise typer.Exit(code=1)

    show_verification_status(verifier.stats())

    img = PILImage.open(image_path)
    console.print(f"[info]Image size:[/] {img.width}x{img.height}")
    console.print()

    with console.status("Verifying...", spinner="dots"):
        result = verifier.verify(img, query)

    # Display results
    table = Table(title="🔍 Verification Result", box=box.DOUBLE_EDGE, border_style="green" if result.accepted else "red")
    table.add_column("Metric", style="stat_key")
    table.add_column("Value")

    decision = "[success]✅ ACCEPTED[/]" if result.accepted else "[error]❌ REJECTED[/]"
    table.add_row("Decision", decision)
    table.add_row("Combined Score", f"[{'score' if result.combined_score > 0.2 else 'score_bad'}]{result.combined_score:.4f}[/]")
    table.add_row("CLIP Score", f"{result.clip_score:.4f}")
    table.add_row("BLIP Score", f"{result.blip_score:.4f}")
    table.add_row("BLIP Caption", result.blip_caption or "[muted]N/A[/]")
    table.add_row("Reason", result.reason)

    console.print(table)
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLEAN COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def clean(
    temp: bool  = typer.Option(True,  "--temp/--no-temp",  help="Clean temp/worker dirs"),
    cache: bool = typer.Option(False, "--cache",           help="Also clear image cache"),
    progress: bool = typer.Option(False, "--progress",     help="Also reset progress DB"),
    all_: bool  = typer.Option(False, "--all",             help="Clean everything"),
) -> None:
    """
    🧹 Clean temporary files, cache, and progress data.
    """
    import shutil
    from config.settings import cfg

    show_banner()

    cleaned = []

    if temp or all_:
        if cfg.paths.temp_dir.exists():
            shutil.rmtree(cfg.paths.temp_dir, ignore_errors=True)
            cleaned.append("temp directory")

    if cache or all_:
        if cfg.paths.cache_db.exists():
            cfg.paths.cache_db.unlink()
            cleaned.append("image cache")

    if progress or all_:
        if cfg.paths.progress_db.exists():
            cfg.paths.progress_db.unlink()
            cleaned.append("progress database")

    if cleaned:
        for item in cleaned:
            console.print(f"  [success]✅ Cleaned:[/] {item}")
    else:
        console.print("[muted]Nothing to clean[/]")

    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PREVIEW COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def preview(
    rows: int = typer.Option(5, "--rows", "-n", help="Number of rows to preview"),
) -> None:
    """
    👁️  Preview CSV data and queries that will be generated.
    """
    import pandas as pd
    from config.settings import cfg
    from core.pipeline import build_query

    show_banner()

    if not cfg.paths.csv_input.exists():
        console.print(f"[error]CSV not found: {cfg.paths.csv_input}[/]")
        raise typer.Exit(code=1)

    df = pd.read_csv(cfg.paths.csv_input)

    table = Table(
        title=f"👁️ Preview (first {rows} rows)",
        box=box.ROUNDED,
        border_style="bright_blue",
    )
    table.add_column("#", style="muted", width=4)
    table.add_column("Query", style="query", min_width=30)
    table.add_column("Text", style="muted", max_width=40)
    table.add_column("Color", width=8)
    table.add_column("CTA", max_width=15)

    for i, row_data in df.head(rows).iterrows():
        query = build_query(row_data, cfg.query)
        text = str(row_data.get("text", ""))[:40]
        color = str(row_data.get("dominant_colour", ""))
        cta = str(row_data.get("call_to_action", ""))

        table.add_row(
            str(i + 1),
            query,
            text,
            color if color != "nan" else "",
            cta if cta != "nan" else "",
        )

    console.print(table)
    console.print(f"\n[muted]Total rows: {len(df)}[/]")
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEFAULT (no command)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    """
    🚀 Ad Generator v4.0 — Production-grade pipeline.

    Run [bold]adgen run[/bold] to start generating ads.
    Run [bold]adgen --help[/bold] to see all commands.
    """
    if ctx.invoked_subcommand is None:
        show_banner()
        console.print("Available commands:\n")
        console.print("  [bold cyan]run[/]      Generate ad images from CSV")
        console.print("  [bold cyan]status[/]   Show pipeline progress")
        console.print("  [bold cyan]config[/]   Show current configuration")
        console.print("  [bold cyan]preview[/]  Preview CSV queries")
        console.print("  [bold cyan]verify[/]   Test image verification")
        console.print("  [bold cyan]cache[/]    Manage image cache")
        console.print("  [bold cyan]clean[/]    Clean temp files")
        console.print()
        console.print("[muted]Run 'python main.py run --help' for detailed options[/]")
        console.print()