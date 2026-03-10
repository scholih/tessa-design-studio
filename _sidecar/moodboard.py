#!/usr/bin/env python3
"""
moodboard.py — Visual reference collection and moodboard generation.

Download image references, analyze visual themes, generate
moodboard grids, extract color palettes.

Usage:
  uv run _sidecar/moodboard.py collect urls.txt --out refs/
  uv run _sidecar/moodboard.py grid refs/ --out moodboard.jpg
  uv run _sidecar/moodboard.py palette refs/ --colors 8
  uv run _sidecar/moodboard.py analyze refs/       # describe visual themes (needs llava)
  uv run _sidecar/moodboard.py keywords refs/      # extract visual keywords for prompts
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console

app = typer.Typer(add_completion=False)
console = Console()


def _download(url: str, dest: Path) -> bool:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        if "image" not in content_type and not url.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            return False
        dest.write_bytes(r.content)
        return True
    except Exception:
        return False


def _image_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


@app.command()
def collect(
    urls_file: Path,
    out: Path = typer.Option(Path("refs"), "--out"),
    prefix: str = typer.Option("ref", "--prefix"),
) -> None:
    """Download images from a list of URLs (one per line)."""
    urls = [u.strip() for u in urls_file.read_text().splitlines() if u.strip() and not u.startswith("#")]
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i, url in enumerate(urls):
        # Guess extension
        ext = Path(url.split("?")[0]).suffix.lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"
        dest = out / f"{prefix}_{i:03d}{ext}"
        if _download(url, dest):
            console.print(f"  ✓ {dest.name}")
            ok += 1
        else:
            console.print(f"  [yellow]✗ {url[:60]}[/yellow]")

    console.print(f"\n[green]Downloaded {ok}/{len(urls)} images to {out}/[/green]")


@app.command()
def grid(
    folder: Path,
    out: Path = typer.Option(Path("moodboard.jpg"), "--out"),
    cols: int = typer.Option(4, "--cols"),
    size: int = typer.Option(300, "--size", help="Each thumbnail size in pixels"),
    padding: int = typer.Option(8, "--padding"),
) -> None:
    """Compose images from a folder into a moodboard grid."""
    from PIL import Image

    images = sorted([f for f in folder.iterdir() if _is_image(f)])
    if not images:
        console.print("[red]No images found[/red]")
        raise typer.Exit(1)

    rows = (len(images) + cols - 1) // cols
    bg_color = (245, 245, 245)
    cell = size + padding
    canvas_w = cols * cell + padding
    canvas_h = rows * cell + padding

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)

    for idx, img_path in enumerate(images):
        try:
            img = Image.open(img_path).convert("RGB")
            img.thumbnail((size, size), Image.LANCZOS)
            # Center crop to square
            w, h = img.size
            if w != h:
                min_dim = min(w, h)
                left = (w - min_dim) // 2
                top = (h - min_dim) // 2
                img = img.crop((left, top, left + min_dim, top + min_dim))
                img = img.resize((size, size), Image.LANCZOS)

            row, col = divmod(idx, cols)
            x = padding + col * cell
            y = padding + row * cell
            canvas.paste(img, (x, y))
        except Exception as e:
            console.print(f"[yellow]Skip {img_path.name}: {e}[/yellow]")

    canvas.save(out, quality=92)
    console.print(f"[green]Moodboard saved: {out} ({len(images)} images, {cols}×{rows} grid)[/green]")


@app.command()
def palette(
    folder: Path,
    colors: int = typer.Option(8, "--colors", "-n"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Extract dominant color palette from a collection of reference images."""
    from PIL import Image
    import numpy as np
    from sklearn.cluster import KMeans

    images = sorted([f for f in folder.iterdir() if _is_image(f)])
    if not images:
        console.print("[red]No images found[/red]")
        raise typer.Exit(1)

    all_pixels = []
    for img_path in images[:20]:
        try:
            img = Image.open(img_path).convert("RGB").resize((50, 50))
            pixels = np.array(img).reshape(-1, 3)
            all_pixels.append(pixels)
        except Exception:
            pass

    if not all_pixels:
        console.print("[red]Could not read any images[/red]")
        raise typer.Exit(1)

    X = np.vstack(all_pixels).astype(float)
    km = KMeans(n_clusters=colors, random_state=42, n_init=10)
    km.fit(X)

    palette_colors = km.cluster_centers_.astype(int)
    lines = [f"# Color Palette ({colors} colors from {len(images)} references)\n"]
    for i, (r, g, b) in enumerate(palette_colors):
        hex_code = f"#{r:02x}{g:02x}{b:02x}".upper()
        lines.append(f"Color {i+1}: {hex_code}  rgb({r}, {g}, {b})")
        console.print(f"  {hex_code}  rgb({r}, {g}, {b})")

    output = "\n".join(lines)
    if out:
        out.write_text(output)
        console.print(f"\nPalette saved to {out}")


@app.command()
def analyze(
    folder: Path,
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Describe visual themes across reference images using llava (multimodal)."""
    import ollama as ol

    images = sorted([f for f in folder.iterdir() if _is_image(f)])[:8]
    if not images:
        console.print("[red]No images found[/red]")
        raise typer.Exit(1)

    console.print(f"Analyzing {len(images)} images with llava...")
    descriptions = []
    for img_path in images:
        try:
            console.print(f"  → {img_path.name}")
            r = ol.chat(
                model="llava:13b",
                messages=[{
                    "role": "user",
                    "content": "Describe this image briefly for a design moodboard. Focus on: mood, colors, materials, forms, style aesthetic. 2-3 sentences.",
                    "images": [_image_to_b64(img_path)],
                }]
            )
            descriptions.append(f"**{img_path.name}**: {r['message']['content']}")
        except Exception as e:
            console.print(f"  [yellow]Skip {img_path.name}: {e}[/yellow]")

    # Synthesize overall mood
    combined = "\n".join(descriptions)
    synth_prompt = f"""Based on these image descriptions from a design moodboard, synthesize the overall visual direction:

{combined}

Output:
1. **Overall mood** (2-3 words)
2. **Visual language** — key aesthetic characteristics
3. **Color story** — how colors feel together
4. **Material/texture direction**
5. **Design prompt keywords** — 10 words useful for AI image generation"""

    import ollama as ol2
    synth = ol2.chat(model="llama3.1:8b", messages=[{"role": "user", "content": synth_prompt}])
    synthesis = synth["message"]["content"]

    output = f"# Moodboard Analysis\n\n## Individual Images\n\n{combined}\n\n## Visual Direction\n\n{synthesis}"
    if out:
        out.write_text(output)
        console.print(f"Analysis saved to {out}")
    else:
        console.print(output)


@app.command()
def keywords(
    folder: Path,
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Extract visual keywords from a moodboard for use in AI image/video prompts."""
    import ollama as ol

    images = sorted([f for f in folder.iterdir() if _is_image(f)])[:6]
    if not images:
        console.print("[red]No images found[/red]")
        raise typer.Exit(1)

    all_keywords = []
    for img_path in images:
        try:
            r = ol.chat(
                model="llava:13b",
                messages=[{
                    "role": "user",
                    "content": "List 8 single keywords describing this image's visual style, mood, and aesthetic. Only keywords, comma-separated, no explanation.",
                    "images": [_image_to_b64(img_path)],
                }]
            )
            kws = [k.strip() for k in r["message"]["content"].split(",")]
            all_keywords.extend(kws)
        except Exception:
            pass

    # Deduplicate and rank by frequency
    from collections import Counter
    counts = Counter(all_keywords)
    top_keywords = [kw for kw, _ in counts.most_common(20)]

    output = ", ".join(top_keywords)
    console.print(f"\n[bold]Visual keywords for prompts:[/bold]")
    console.print(output)

    if out:
        out.write_text(output)
        console.print(f"\nSaved to {out}")


if __name__ == "__main__":
    app()
