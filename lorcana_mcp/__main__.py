from __future__ import annotations

import click
from importlib.metadata import version as _pkg_version


@click.group()
@click.version_option(version=_pkg_version("lorcana-mcp"), prog_name="lorcana-mcp")
def cli() -> None:
    """Lorcana MCP server — connect Claude to your Disney Lorcana collection."""


@cli.command()
def serve() -> None:
    """Start the MCP server (stdio transport for Claude)."""
    from .server import mcp

    mcp.run()


@cli.group()
def cache() -> None:
    """Inspect or manage the local API response cache."""


@cache.command("stats")
def cache_stats() -> None:
    """Show cache entry count, expiry status, and file size."""
    from . import cache as c

    s = c.stats()
    click.echo(f"Entries:  {s['entries']} total, {s['expired']} expired")
    click.echo(f"Size:     {s['size_bytes'] / 1024:.1f} KB")
    click.echo("TTL:      24 hours (card data refreshes daily)")


@cache.command("clear")
def cache_clear() -> None:
    """Delete all cached API responses (forces fresh fetch on next run)."""
    from . import cache as c

    count = c.clear()
    click.echo(f"Cleared {count} cache entries.")


if __name__ == "__main__":
    cli()
