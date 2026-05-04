"""CLI entry points for pitindex.

Mirrors the shape of ``pitedgar``'s CLI: a Click group with one
sub-command per pipeline stage / query mode, ``--format`` flag on
read-style commands to switch between table / JSON / CSV output.
"""

from __future__ import annotations

import json
import sys
from typing import Literal

import click
import pandas as pd

from . import (
    __version__,
    get_constituents,
    get_constituents_history,
    info,
    update,
)

OutputFormat = Literal["table", "json", "csv"]


def _emit(df: pd.DataFrame, fmt: str) -> None:
    if fmt == "json":
        click.echo(df.to_json(orient="records", date_format="iso"))
    elif fmt == "csv":
        df.to_csv(sys.stdout, index=False)
    else:  # table
        with pd.option_context("display.max_rows", None, "display.max_columns", None, "display.width", 200):
            click.echo(df.to_string(index=False))


@click.group()
@click.version_option(__version__, prog_name="pitindex")
def cli() -> None:
    """pitindex — point-in-time index constituents from free public sources."""


@cli.command("info")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    show_default=True,
)
def cmd_info(fmt: str) -> None:
    """Show metadata about the loaded dataset (build time, sources, staleness)."""
    payload = info()
    if fmt == "json":
        click.echo(json.dumps(payload, indent=2, default=str))
        return
    width = max(len(k) for k in payload)
    for k, v in payload.items():
        click.echo(f"{k.ljust(width)}  {v}")


@cli.command("get")
@click.option(
    "--as-of",
    "as_of",
    required=True,
    help="Date in YYYY-MM-DD format.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    show_default=True,
)
@click.option(
    "--tickers-only",
    is_flag=True,
    default=False,
    help="Print just the ticker symbols, one per line.",
)
def cmd_get(as_of: str, fmt: str, tickers_only: bool) -> None:
    """Print the index membership at AS_OF."""
    try:
        df = get_constituents(as_of)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if tickers_only:
        for t in df["ticker"]:
            click.echo(t)
        return
    _emit(df, fmt)


@cli.command("history")
@click.option("--start", required=True, help="Start date YYYY-MM-DD.")
@click.option("--end", required=True, help="End date YYYY-MM-DD.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "csv"]),
    default="csv",
    show_default=True,
)
def cmd_history(start: str, end: str, fmt: str) -> None:
    """Print one membership snapshot per change date in [START, END]."""
    try:
        df = get_constituents_history(start, end)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    _emit(df, fmt)


@cli.command("update")
@click.option("--force", is_flag=True, default=False, help="Bypass the 24h cache freshness check.")
def cmd_update(force: bool) -> None:
    """Rebuild the local data cache from upstream sources."""
    try:
        meta = update(force=force)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Cache refreshed. Build timestamp: {meta.get('build_timestamp_utc')}")
    click.echo(f"Roster size: {meta.get('current_size')}, events: {meta.get('events_count')}")


@cli.command("build")
@click.option("--start-date", default=None, help="Override the bootstrap date (default 2005-01-03).")
@click.option(
    "--max-diff-ratio",
    type=float,
    default=None,
    help="Override the reconciliation tolerance (default 0.05).",
)
@click.option("-v", "--verbose", is_flag=True, default=False)
def cmd_build(start_date: str | None, max_diff_ratio: float | None, verbose: bool) -> None:
    """Run the full build pipeline against live upstream sources.

    Writes the regenerated CSVs into ``pitindex/data/`` (the in-repo
    location, not the user cache) so the result is committable. Use
    ``pitindex update`` instead for a per-user cache refresh.
    """
    try:
        # Deferred: scripts/ is an optional build-time package not present
        # when only runtime extras are installed.
        from scripts import build_dataset  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - exercised only without the build extra
        raise click.ClickException(
            "The build pipeline requires the [build] extra. Install with: pip install 'pitindex[build]'"
        ) from exc

    argv: list[str] = []
    if start_date:
        argv += ["--start-date", start_date]
    if max_diff_ratio is not None:
        argv += ["--max-diff-ratio", str(max_diff_ratio)]
    if verbose:
        argv += ["-v"]
    rc = build_dataset.main(argv)
    if rc != 0:
        raise click.ClickException(f"Build failed with exit code {rc}.")


if __name__ == "__main__":  # pragma: no cover
    cli()
