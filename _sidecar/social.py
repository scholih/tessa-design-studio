#!/usr/bin/env python3
"""
social.py — Instagram content tools for @amaize.

Generate captions, hashtags, content calendars, and bio copy
for a design student's personal brand on Instagram.

Usage:
  uv run _sidecar/social.py caption "minimal ceramic lamp, warm studio light"
  uv run _sidecar/social.py caption image.jpg          # describe from image (needs llava)
  uv run _sidecar/social.py hashtags "sustainable packaging design"
  uv run _sidecar/social.py calendar brief.md --days 7
  uv run _sidecar/social.py bio "industrial design student, TU Delft, sustainability focus"
  uv run _sidecar/social.py carousel brief.md --slides 5
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
VISION_MODEL = "llava:13b"

BRAND_CONTEXT = """
You are writing Instagram content for @amaize — a design student's personal brand.
The designer studies Industrial Design at TU Delft, focuses on sustainability,
human-centered design, and thoughtful materiality. The aesthetic is clean, curious,
and honest — not corporate, not over-polished. Think: design process visible,
materials celebrated, ideas over perfection.

Tone: warm, direct, curious. Not hashtag-spammy. Not fake-inspirational.
"""

NICHES = [
    "industrialdesign", "productdesign", "designstudent", "tudelft",
    "sustainabledesign", "humancentereddesign", "designprocess", "materialdesign",
    "designthinking", "designinspiration", "makerculture", "prototype",
    "sketchbook", "designcommunity", "delft", "dutchdesign", "designlife",
    "conceptdesign", "designresearch", "objectdesign",
]


def _ask(prompt: str, model: str = MODEL) -> str:
    r = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return r["message"]["content"]


def _describe_image(path: Path) -> str:
    import base64
    b64 = base64.b64encode(path.read_bytes()).decode()
    r = ollama.chat(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": "Describe this design/product image for Instagram. What does it show? Materials, mood, context, aesthetic. 3-4 sentences.",
            "images": [b64],
        }]
    )
    return r["message"]["content"]


@app.command()
def caption(
    subject: str,
    tone: str = typer.Option("curious,warm", "--tone", "-t", help="Tone keywords"),
    length: str = typer.Option("medium", "--length", "-l", help="short/medium/long"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Write an Instagram caption. Subject can be text or path to an image."""
    # Check if subject is an image file
    subject_path = Path(subject)
    if subject_path.exists() and subject_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        console.print(f"  Analyzing image with llava...")
        description = _describe_image(subject_path)
        console.print(f"  [dim]Image: {description[:100]}...[/dim]")
    else:
        description = subject

    length_guide = {
        "short": "2-3 sentences, punchy",
        "medium": "4-6 sentences, one idea developed",
        "long": "8-10 sentences, storytelling, show the process",
    }.get(length, "4-6 sentences")

    prompt = f"""{BRAND_CONTEXT}

Write an Instagram caption for this content:
{description}

Tone: {tone}
Length: {length_guide}

Rules:
- Start with a hook (not "I" or "Today")
- No fake inspiration ("Every design tells a story..." type openers)
- Show genuine curiosity or process thinking
- End with either a question to the audience OR a quiet statement
- No emojis unless they genuinely add something
- NO hashtags in the caption (they go in the first comment)

Write only the caption text, nothing else."""

    result = _ask(prompt)
    console.print(Panel(result, title="[bold]Caption for @amaize[/bold]", border_style="magenta"))

    if out:
        out.write_text(result)
        console.print(f"Saved to {out}")


@app.command()
def hashtags(
    topic: str,
    count: int = typer.Option(20, "--count", "-n"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate a hashtag set for a post topic."""
    prompt = f"""{BRAND_CONTEXT}

Generate {count} Instagram hashtags for this topic: {topic}

Mix of:
- 5 broad design hashtags (high volume, >500k posts)
- 8 niche design hashtags (medium volume, 10k-500k posts)
- 4 community hashtags (engaged, <50k posts)
- 3 location/school hashtags (tudelft, dutchdesign, delft etc)

From this pool of relevant tags, pick the best fit:
{', '.join('#' + t for t in NICHES)}
...and suggest additional relevant ones.

Output: just the hashtags, space-separated, starting with #. No explanation."""

    result = _ask(prompt)

    console.print(Panel(result, title=f"[bold]Hashtags: {topic}[/bold]", border_style="cyan"))
    console.print("\n[dim]Tip: paste these in the first comment, not the caption[/dim]")

    if out:
        out.write_text(result)


@app.command()
def calendar(
    source: str,
    days: int = typer.Option(7, "--days", "-d"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Plan a content calendar from a project brief or description."""
    source_path = Path(source)
    if source_path.exists():
        context = source_path.read_text(encoding="utf-8")[:3000]
    else:
        context = source

    prompt = f"""{BRAND_CONTEXT}

Create a {days}-day Instagram content calendar based on this project/context:

{context}

For each day provide:
- **Day N** — content type (process shot / sketch / material / final / behind-the-scenes / question)
- **What to photograph/show** — specific, actionable
- **Caption angle** — one sentence describing the story/hook
- **Best time to post** — (morning 8-9h / lunch 12-13h / evening 19-21h)

Make it feel like a natural design process unfolding, not a marketing campaign.
Vary the content types — don't post the same format two days in a row."""

    result = _ask(prompt)
    console.print(Panel(result, title=f"[bold]{days}-Day Content Calendar[/bold]", border_style="green"))

    if out:
        out.write_text(result)
        console.print(f"Calendar saved to {out}")


@app.command()
def bio(
    description: str,
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Write Instagram bio options (150 char limit)."""
    prompt = f"""{BRAND_CONTEXT}

Write 3 Instagram bio options for @amaize based on:
{description}

Rules:
- Max 150 characters each
- No buzzwords (passionate, creative, innovative)
- Can include 1 emoji max if it genuinely fits
- Show what she does + who she is, not what she aspires to be
- TU Delft mention welcome but not required in all versions

Format:
Option 1: [bio text] ({{}}/150 chars)
Option 2: [bio text] ({{}}/150 chars)
Option 3: [bio text] ({{}}/150 chars)"""

    result = _ask(prompt)
    console.print(Panel(result, title="[bold]Bio Options for @amaize[/bold]", border_style="yellow"))

    if out:
        out.write_text(result)


@app.command()
def carousel(
    source: str,
    slides: int = typer.Option(5, "--slides", "-n"),
    topic: str = typer.Option("", "--topic", "-t"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Write copy for a carousel post (multi-slide Instagram post)."""
    source_path = Path(source)
    if source_path.exists():
        context = source_path.read_text(encoding="utf-8")[:3000]
    else:
        context = source

    if topic:
        context = f"Topic: {topic}\n\n{context}"

    prompt = f"""{BRAND_CONTEXT}

Write a {slides}-slide Instagram carousel based on:
{context}

Format for each slide:
**Slide N** (headline — max 8 words)
Body text: 2-3 sentences max. Short. Scannable.

Rules:
- Slide 1: hook — make them swipe
- Middle slides: substance — teach, show, or reveal something
- Last slide: call to action or open question
- Each slide must work as a standalone thought
- No "swipe to see more" filler text"""

    result = _ask(prompt)
    console.print(Panel(result, title=f"[bold]{slides}-Slide Carousel[/bold]", border_style="blue"))

    if out:
        out.write_text(result)
        console.print(f"Carousel saved to {out}")


@app.command()
def analyze(
    handle: str = typer.Argument("amaize", help="Instagram handle to analyze (without @)"),
) -> None:
    """Tips for growing a design student Instagram account."""
    prompt = f"""{BRAND_CONTEXT}

Give practical, specific advice for growing @{handle} as a design student's Instagram.

Cover:
1. **Content mix** — what ratio of content types works for design audiences
2. **Posting rhythm** — realistic cadence for a busy student
3. **What performs well** — in the industrial/product design niche specifically
4. **What to avoid** — common mistakes design students make on Instagram
5. **Story vs Feed** — how to use each
6. **Engagement tactics** — that feel genuine, not spammy

Be specific and honest. No generic social media advice."""

    result = _ask(prompt)
    console.print(Panel(result, title=f"[bold]Instagram Strategy for @{handle}[/bold]", border_style="green"))


if __name__ == "__main__":
    app()
