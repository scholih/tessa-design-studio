#!/usr/bin/env python3
"""
cluster.py — User research theme clustering for design students.

Turn interview transcripts, survey responses, and sticky notes
into structured affinity diagrams and insight clusters.

Usage:
  uv run _sidecar/cluster.py affinity interviews/         # cluster interview folder
  uv run _sidecar/cluster.py affinity notes.txt --clusters 6
  uv run _sidecar/cluster.py quotes interviews/ --theme "pain points"
  uv run _sidecar/cluster.py personas interviews/ --count 3
  uv run _sidecar/cluster.py insights interviews/ --out insights.md
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Annotated

import numpy as np
import ollama
import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(add_completion=False)
console = Console()

EMBED_MODEL = "nomic-embed-text"
REASON_MODEL = "llama3.1:8b"
FAST_MODEL = "llama3.2:3b"


def _embed(text: str) -> list[float]:
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


def _ask(prompt: str, model: str = REASON_MODEL) -> str:
    r = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return r["message"]["content"]


def _read_folder(folder: Path) -> list[dict]:
    """Read all .txt and .md files from a folder as interview transcripts."""
    items = []
    for f in sorted(folder.glob("**/*.txt")) + sorted(folder.glob("**/*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        items.append({"source": f.name, "text": text})
    return items


def _sentences(text: str) -> list[str]:
    """Split text into meaningful sentences/quotes (min 20 chars)."""
    import re
    parts = re.split(r"[.!?\n]+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


@app.command()
def affinity(
    source: Path,
    clusters: int = typer.Option(5, "--clusters", "-c"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Cluster interview/survey data into affinity groups — digital affinity diagram."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import normalize

    # Load data
    if source.is_dir():
        docs = _read_folder(source)
    else:
        docs = [{"source": source.name, "text": source.read_text()}]

    if not docs:
        console.print("[red]No text files found[/red]")
        raise typer.Exit(1)

    # Extract sentences/quotes
    quotes = []
    for doc in docs:
        for sent in _sentences(doc["text"]):
            quotes.append({"source": doc["source"], "text": sent})

    console.print(f"Clustering {len(quotes)} quotes into {clusters} groups...")

    # Embed
    vecs = []
    for q in quotes:
        q["embedding"] = _embed(q["text"])
        vecs.append(q["embedding"])

    X = normalize(np.array(vecs))
    km = KMeans(n_clusters=clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    # Group by cluster
    groups: dict[int, list[dict]] = {i: [] for i in range(clusters)}
    for idx, label in enumerate(labels):
        groups[label].append(quotes[idx])

    # Name clusters
    lines = [f"# Affinity Diagram — {clusters} clusters\n\n"]
    lines.append(f"*{len(quotes)} quotes from {len(docs)} sources*\n")

    for gid, items in groups.items():
        sample = " | ".join(q["text"] for q in items[:4])
        name_prompt = f"Name this user research theme in 4 words: {sample[:400]}"
        name = _ask(name_prompt, FAST_MODEL).strip().strip('"').strip("'")
        lines.append(f"\n## {name} ({len(items)} quotes)")
        for item in items[:6]:
            lines.append(f'> "{item["text"]}" — *{item["source"]}*')

    output = "\n".join(lines)
    if out:
        out.write_text(output)
        console.print(f"[green]Affinity diagram saved to {out}[/green]")
    else:
        console.print(output)


@app.command()
def quotes(
    source: Path,
    theme: str = typer.Option(..., "--theme", "-t", help="Theme to search for"),
    top: int = typer.Option(10, "--top", "-n"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Find most relevant quotes for a specific design theme."""
    if source.is_dir():
        docs = _read_folder(source)
    else:
        docs = [{"source": source.name, "text": source.read_text()}]

    all_quotes = []
    for doc in docs:
        for sent in _sentences(doc["text"]):
            all_quotes.append({"source": doc["source"], "text": sent})

    theme_vec = np.array(_embed(theme))
    scored = []
    for q in all_quotes:
        vec = np.array(_embed(q["text"]))
        score = float(np.dot(theme_vec, vec) / (np.linalg.norm(theme_vec) * np.linalg.norm(vec) + 1e-9))
        scored.append((score, q))

    scored.sort(key=lambda x: x[0], reverse=True)
    lines = [f"# Top {top} quotes for: \"{theme}\"\n"]
    for score, q in scored[:top]:
        lines.append(f'> "{q["text"]}"')
        lines.append(f'*{q["source"]} — relevance: {score:.2f}*\n')

    output = "\n".join(lines)
    if out:
        out.write_text(output)
    else:
        console.print(output)


@app.command()
def personas(
    source: Path,
    count: int = typer.Option(3, "--count", "-n", help="Number of personas"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate design personas from interview data."""
    if source.is_dir():
        docs = _read_folder(source)
    else:
        docs = [{"source": source.name, "text": source.read_text()}]

    combined = "\n\n".join(f"[{d['source']}]\n{d['text'][:1500]}" for d in docs[:6])
    prompt = f"""Based on these user research transcripts, create {count} realistic design personas.

For each persona include:
- **Name & Age** (fictional but realistic)
- **Occupation & Context**
- **Goals** — what they're trying to achieve
- **Frustrations** — what gets in their way
- **Behaviours** — relevant patterns from the research
- **A quote** that captures their mindset
- **Design implication** — what this means for the design

Research data:
{combined[:5000]}"""

    result = _ask(prompt, REASON_MODEL)
    if out:
        out.write_text(result)
        console.print(f"Personas saved to {out}")
    else:
        console.print(Panel(result, title=f"[bold]{count} Design Personas[/bold]", border_style="magenta"))


@app.command()
def insights(
    source: Path,
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Extract key design insights — the 'how might we' statements."""
    if source.is_dir():
        docs = _read_folder(source)
    else:
        docs = [{"source": source.name, "text": source.read_text()}]

    combined = "\n\n".join(f"[{d['source']}]\n{d['text'][:1200]}" for d in docs[:8])
    prompt = f"""Analyze these user research transcripts as an experienced design researcher.

Output:
1. **Key Insights** (5-8): What are the most important things you learned about users?
   Format: "Users [observation] because [underlying reason]"

2. **How Might We statements** (5-8): Turn insights into design opportunities.
   Format: "How might we [help users do X] so that [outcome]?"

3. **Design Tensions**: What conflicting needs did you find?

4. **Surprising findings**: What was unexpected?

Research data:
{combined[:5000]}"""

    result = _ask(prompt, REASON_MODEL)
    if out:
        out.write_text(result)
        console.print(f"Insights saved to {out}")
    else:
        console.print(Panel(result, title="[bold]Design Insights[/bold]", border_style="cyan"))


if __name__ == "__main__":
    app()
