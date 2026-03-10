#!/usr/bin/env python3
"""
video_prompt.py — Structured video/motion prompt builder for design students.

Generate optimized prompts for Runway, Kling, Veo, Sora, and Pika.
Tailored for industrial design: product shots, user scenarios,
concept animations, design process documentation.

Usage:
  uv run _sidecar/video_prompt.py product "ergonomic water bottle" --style minimal
  uv run _sidecar/video_prompt.py scenario "user unpacking sustainable packaging"
  uv run _sidecar/video_prompt.py concept "modular furniture system" --mood "calm,modern"
  uv run _sidecar/video_prompt.py sequence brief.md   # generate a shot list from a brief
  uv run _sidecar/video_prompt.py refine prompt.txt   # improve an existing prompt
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import ollama
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(add_completion=False)
console = Console()

MODEL = "llama3.1:8b"

STYLES = {
    "minimal": "clean white studio, soft diffused lighting, minimal background, product photography",
    "lifestyle": "real-world context, natural lighting, authentic human interaction, documentary feel",
    "cinematic": "dramatic lighting, shallow depth of field, film grain, cinematic color grading",
    "concept": "3D render aesthetic, studio lighting, floating in space, futuristic clean",
    "nature": "natural outdoor setting, golden hour lighting, organic textures, environmental context",
    "urban": "city environment, contemporary architecture, street-level perspective, modern lifestyle",
}

PLATFORMS = {
    "runway": {"max_seconds": 16, "aspect": "16:9 or 9:16", "note": "Add 'Gen-3 Alpha' style cues"},
    "kling": {"max_seconds": 30, "aspect": "16:9", "note": "Strong on realistic motion and physics"},
    "veo": {"max_seconds": 60, "aspect": "16:9", "note": "Google Veo — very cinematic, high quality"},
    "sora": {"max_seconds": 60, "aspect": "16:9 or 1:1", "note": "Strong on complex scenes and physics"},
    "pika": {"max_seconds": 10, "aspect": "16:9", "note": "Good for short loops and transitions"},
}


def _ask(prompt: str) -> str:
    r = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
    return r["message"]["content"]


def _show_prompt(prompt_text: str, title: str, platform: str) -> None:
    info = PLATFORMS.get(platform, {})
    console.print(Panel(
        prompt_text,
        title=f"[bold]{title}[/bold] — optimized for [cyan]{platform.upper()}[/cyan]",
        subtitle=f"[dim]{info.get('note', '')} | max {info.get('max_seconds', '?')}s | {info.get('aspect', '')}[/dim]",
        border_style="green",
    ))


@app.command()
def product(
    description: str,
    style: str = typer.Option("minimal", help=f"Style: {', '.join(STYLES.keys())}"),
    platform: str = typer.Option("runway", help=f"Platform: {', '.join(PLATFORMS.keys())}"),
    duration: int = typer.Option(8, "--duration", "-d", help="Target duration in seconds"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate a product showcase video prompt."""
    style_desc = STYLES.get(style, style)
    platform_info = PLATFORMS.get(platform, {})

    prompt = f"""Create a detailed video generation prompt for a product showcase video.

Product: {description}
Visual style: {style_desc}
Duration: approximately {duration} seconds
Platform: {platform} ({platform_info.get('note', '')})

The prompt should include:
- Opening shot description
- Camera movement (slow pan, orbit, pull back, etc.)
- Lighting setup
- Background/context
- Product details to highlight
- Mood and atmosphere
- Any motion/animation of the product itself

Write it as a single cohesive paragraph optimized for {platform} video generation.
Be specific and visual. No bullet points — one flowing prompt."""

    result = _ask(prompt)
    _show_prompt(result, f"Product: {description}", platform)
    if out:
        out.write_text(result)


@app.command()
def scenario(
    description: str,
    platform: str = typer.Option("kling", help=f"Platform: {', '.join(PLATFORMS.keys())}"),
    duration: int = typer.Option(12, "--duration", "-d"),
    mood: str = typer.Option("authentic,warm", "--mood"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate a user scenario / use context video prompt."""
    prompt = f"""Create a detailed video generation prompt for a user scenario showing a product in use.

Scenario: {description}
Mood/tone: {mood}
Duration: approximately {duration} seconds
Platform: {platform}

Show a realistic human using or interacting with the product in context.
The prompt should describe:
- The person (brief, non-specific demographic)
- The environment/setting
- The action being performed
- Camera angle and movement
- Lighting and time of day
- Emotional tone

Write as one flowing paragraph optimized for {platform}. Be cinematic and specific."""

    result = _ask(prompt)
    _show_prompt(result, f"Scenario: {description}", platform)
    if out:
        out.write_text(result)


@app.command()
def concept(
    description: str,
    platform: str = typer.Option("sora", help=f"Platform: {', '.join(PLATFORMS.keys())}"),
    mood: str = typer.Option("innovative,clean", "--mood"),
    duration: int = typer.Option(15, "--duration", "-d"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate a concept/vision video prompt — abstract or future-forward."""
    prompt = f"""Create a video generation prompt for a design concept visualization.

Concept: {description}
Mood: {mood}
Duration: approximately {duration} seconds
Platform: {platform}

This should feel like a design vision or concept film — not a literal product demo.
Think: how might a design studio present this concept at an exhibition?

Include:
- Visual metaphor or abstract representation
- Transitions and transformations if applicable
- Color palette and texture
- Camera movement
- Any text/typography moments if relevant
- Ending frame

Write as one flowing cinematic prompt."""

    result = _ask(prompt)
    _show_prompt(result, f"Concept: {description}", platform)
    if out:
        out.write_text(result)


@app.command()
def sequence(
    brief_file: Path,
    shots: int = typer.Option(5, "--shots", "-n"),
    platform: str = typer.Option("runway", help=f"Platform: {', '.join(PLATFORMS.keys())}"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate a full shot list from a design brief."""
    brief_text = brief_file.read_text(encoding="utf-8")[:3000]
    platform_info = PLATFORMS.get(platform, {})

    prompt = f"""You are a design film director creating a {shots}-shot video sequence for a design presentation.

Based on this design brief, create {shots} individual video prompts that together tell the story of this design.

Platform: {platform} (max {platform_info.get('max_seconds', 16)}s per shot, {platform_info.get('aspect', '16:9')})

For each shot provide:
- Shot number and purpose (establishing/detail/scenario/closing)
- Duration (seconds)
- The full video generation prompt (1 paragraph)
- Transition note to next shot

Design brief:
{brief_text}"""

    result = _ask(prompt)
    if out:
        out.write_text(result)
        console.print(f"Shot list saved to {out}")
    else:
        console.print(Panel(result, title=f"[bold]{shots}-Shot Sequence[/bold]", border_style="yellow"))


@app.command()
def refine(
    prompt_file: Path,
    platform: str = typer.Option("runway", help=f"Platform: {', '.join(PLATFORMS.keys())}"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Improve an existing video prompt for a specific platform."""
    existing = prompt_file.read_text(encoding="utf-8")
    platform_info = PLATFORMS.get(platform, {})

    prompt = f"""Improve this video generation prompt for {platform}.

Platform notes: {platform_info.get('note', '')}
Aspect ratio: {platform_info.get('aspect', '16:9')}
Max duration: {platform_info.get('max_seconds', 16)}s

Improve by:
- Making camera movements more specific
- Adding lighting details
- Ensuring the pacing fits {platform_info.get('max_seconds', 16)} seconds
- Using terminology that {platform} responds well to
- Removing anything that AI video models struggle with (text, multiple faces, complex physics)

Original prompt:
{existing}

Output only the improved prompt, no explanation."""

    result = _ask(prompt)
    _show_prompt(result, f"Refined for {platform}", platform)
    if out:
        out.write_text(result)


@app.command()
def platforms() -> None:
    """Show platform comparison and capabilities."""
    t = Table(title="Video Generation Platforms")
    t.add_column("Platform", style="cyan")
    t.add_column("Max Duration")
    t.add_column("Aspect Ratio")
    t.add_column("Best For")

    best_for = {
        "runway": "Quick iterations, concept videos, motion graphics",
        "kling": "Realistic human interaction, product use scenarios",
        "veo": "Cinematic quality, long-form concept films",
        "sora": "Complex scenes, physics, abstract concepts",
        "pika": "Short loops, transitions, social content",
    }
    for name, info in PLATFORMS.items():
        t.add_row(name.upper(), f"{info['max_seconds']}s", info["aspect"], best_for.get(name, ""))
    console.print(t)


if __name__ == "__main__":
    app()
