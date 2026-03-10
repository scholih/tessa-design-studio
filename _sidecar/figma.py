#!/usr/bin/env python3
"""
figma.py — Figma API toolkit for design students.

Export frames, list components, extract design tokens,
generate asset inventories.

Requires: FIGMA_TOKEN environment variable
  export FIGMA_TOKEN=your_personal_access_token
  (Get from Figma → Account Settings → Personal Access Tokens)

Usage:
  uv run _sidecar/figma.py info <file_key>
  uv run _sidecar/figma.py frames <file_key> --out exports/
  uv run _sidecar/figma.py tokens <file_key>
  uv run _sidecar/figma.py inventory <file_key>
  uv run _sidecar/figma.py thumbnail <file_key> --out thumb.png
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(add_completion=False)
console = Console()

BASE = "https://api.figma.com/v1"


def _token() -> str:
    token = os.environ.get("FIGMA_TOKEN", "")
    if not token:
        console.print("[red]FIGMA_TOKEN not set.[/red]")
        console.print("Get it from Figma → Account Settings → Personal Access Tokens")
        console.print("Then run: export FIGMA_TOKEN=your_token")
        raise typer.Exit(1)
    return token


def _get(path: str) -> dict:
    r = httpx.get(f"{BASE}{path}", headers={"X-Figma-Token": _token()}, timeout=30)
    r.raise_for_status()
    return r.json()


def _flatten_nodes(node: dict, result: list[dict], depth: int = 0) -> None:
    result.append({**node, "_depth": depth})
    for child in node.get("children", []):
        _flatten_nodes(child, result, depth + 1)


@app.command()
def info(file_key: str) -> None:
    """Show basic info about a Figma file."""
    data = _get(f"/files/{file_key}?depth=1")
    name = data.get("name", "Unknown")
    pages = data.get("document", {}).get("children", [])
    console.print(f"\n[bold]{name}[/bold]")
    console.print(f"Pages: {len(pages)}")
    for p in pages:
        console.print(f"  • {p['name']}")
    console.print(f"\nLast modified: {data.get('lastModified', 'unknown')}")


@app.command()
def frames(
    file_key: str,
    out: Path = typer.Option(Path("exports"), "--out"),
    scale: float = typer.Option(2.0, "--scale", help="Export scale (1=72dpi, 2=144dpi, 3=216dpi)"),
    fmt: str = typer.Option("png", "--format", help="png|jpg|svg|pdf"),
) -> None:
    """Export all top-level frames as images."""
    data = _get(f"/files/{file_key}?depth=2")
    pages = data.get("document", {}).get("children", [])

    frame_ids = []
    frame_names = {}
    for page in pages:
        for child in page.get("children", []):
            if child["type"] in ("FRAME", "COMPONENT", "SECTION"):
                frame_ids.append(child["id"])
                frame_names[child["id"]] = f"{page['name']}_{child['name']}"

    if not frame_ids:
        console.print("[yellow]No frames found.[/yellow]")
        raise typer.Exit(0)

    console.print(f"Exporting {len(frame_ids)} frames at {scale}x as {fmt}...")
    ids_str = ",".join(frame_ids[:50])  # API limit
    export_data = _get(f"/images/{file_key}?ids={ids_str}&scale={scale}&format={fmt}")
    images = export_data.get("images", {})

    out.mkdir(parents=True, exist_ok=True)
    for fid, url in images.items():
        if not url:
            continue
        name = frame_names.get(fid, fid).replace("/", "_").replace(" ", "_")
        filepath = out / f"{name}.{fmt}"
        r = httpx.get(url, timeout=60)
        filepath.write_bytes(r.content)
        console.print(f"  ✓ {filepath}")

    console.print(f"\n[green]Exported {len(images)} frames to {out}/[/green]")


@app.command()
def tokens(
    file_key: str,
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Extract design tokens — colors, typography, spacing from local styles."""
    data = _get(f"/files/{file_key}/styles")
    styles = data.get("meta", {}).get("styles", [])

    t = Table(title="Design Tokens")
    t.add_column("Type", style="cyan")
    t.add_column("Name", style="green")
    t.add_column("Key")

    tokens_by_type: dict[str, list] = {}
    for s in styles:
        stype = s.get("style_type", "UNKNOWN")
        tokens_by_type.setdefault(stype, []).append(s)
        t.add_row(stype, s.get("name", ""), s.get("key", ""))

    console.print(t)
    console.print(f"\nTotal: {len(styles)} tokens")
    for stype, items in tokens_by_type.items():
        console.print(f"  {stype}: {len(items)}")

    if out:
        out.write_text(str({k: [s["name"] for s in v] for k, v in tokens_by_type.items()}))
        console.print(f"Saved to {out}")


@app.command()
def inventory(
    file_key: str,
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate a component inventory — all components with descriptions."""
    data = _get(f"/files/{file_key}/components")
    components = data.get("meta", {}).get("components", [])

    lines = [f"# Figma Component Inventory\n", f"Total components: {len(components)}\n"]
    by_page: dict[str, list] = {}
    for c in components:
        containing = c.get("containing_frame", {}).get("pageName", "Unknown")
        by_page.setdefault(containing, []).append(c)

    for page, comps in by_page.items():
        lines.append(f"\n## {page} ({len(comps)} components)")
        for c in comps:
            name = c.get("name", "unnamed")
            desc = c.get("description", "")
            lines.append(f"- **{name}**{': ' + desc if desc else ''}")

    output = "\n".join(lines)
    if out:
        out.write_text(output)
        console.print(f"Inventory saved to {out}")
    else:
        console.print(output)


@app.command()
def thumbnail(
    file_key: str,
    out: Path = typer.Option(Path("thumbnail.png"), "--out"),
) -> None:
    """Download the file thumbnail."""
    data = _get(f"/files/{file_key}?geometry=paths")
    thumb_url = data.get("thumbnailUrl", "")
    if not thumb_url:
        console.print("[yellow]No thumbnail available[/yellow]")
        raise typer.Exit(1)
    r = httpx.get(thumb_url, timeout=30)
    out.write_bytes(r.content)
    console.print(f"Thumbnail saved to {out}")


if __name__ == "__main__":
    app()
