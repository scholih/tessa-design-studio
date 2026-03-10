#!/usr/bin/env python3
"""
research.py — Literature research toolkit for design students.

Analyze PDFs, extract insights, semantic search across papers,
cluster themes from multiple sources.

Usage:
  uv run _sidecar/research.py summarize paper.pdf
  uv run _sidecar/research.py extract paper.pdf --topics "sustainability,user needs,materials"
  uv run _sidecar/research.py index papers/          # build semantic index of a folder
  uv run _sidecar/research.py search "embodied cognition" --index research.index
  uv run _sidecar/research.py cluster papers/ --themes 5   # find 5 major themes
  uv run _sidecar/research.py brief papers/               # generate design brief from literature
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Annotated

import numpy as np
import ollama
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import track

app = typer.Typer(add_completion=False)
console = Console()

EMBED_MODEL = "nomic-embed-text"
REASON_MODEL = "llama3.1:8b"
EXTRACT_MODEL = "mistral:7b"


def _extract_text(pdf_path: Path) -> str:
    """Extract text from PDF."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
    except Exception:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        return "\n".join(p.extract_text() or "" for p in reader.pages)


def _chunk(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), size - overlap):
        chunk = " ".join(words[i:i + size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _embed(text: str) -> list[float]:
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


def _ask(prompt: str, model: str = REASON_MODEL) -> str:
    response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


@app.command()
def summarize(
    file: Path,
    out: Annotated[Path | None, typer.Option("--out")] = None,
    depth: str = typer.Option("default", help="fast|default|deep"),
) -> None:
    """Summarize a research paper — key findings, methods, relevance to design."""
    model = {"fast": "llama3.2:3b", "default": REASON_MODEL, "deep": "llama3.1:70b"}[depth]
    console.print(f"[dim]Reading {file.name}...[/dim]")
    text = _extract_text(file)[:8000]  # first ~8k words
    prompt = f"""You are helping an Industrial Design master student understand a research paper.

Summarize this paper with:
1. **Core argument** (1-2 sentences)
2. **Key findings** (3-5 bullet points)
3. **Methods used** (brief)
4. **Design relevance** — how could this inform a design project?
5. **Quotes worth keeping** (2-3 most useful direct quotes)

Paper text:
{text}"""
    result = _ask(prompt, model)
    if out:
        out.write_text(result)
        console.print(f"Saved to {out}")
    else:
        console.print(Panel(result, title=f"[bold]{file.name}[/bold]", border_style="blue"))


@app.command()
def extract(
    file: Path,
    topics: str = typer.Option("", "--topics", help="Comma-separated topics to focus on"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Extract structured insights from a paper around specific design topics."""
    text = _extract_text(file)[:6000]
    topic_str = topics or "user needs, sustainability, materials, interaction, form, context of use"
    prompt = f"""Extract structured information from this research paper relevant to Industrial Design.

For each of these topics: {topic_str}

Output as JSON with this structure:
{{
  "topic_name": {{
    "finding": "what the paper says",
    "quote": "relevant direct quote if any",
    "design_implication": "how this could influence a design decision"
  }}
}}

Only include topics that are actually addressed in the paper. Skip ones with no relevant content.

Paper:
{text}"""
    result = _ask(prompt, EXTRACT_MODEL)
    # Try to extract JSON block
    if "```json" in result:
        result = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
        result = result.split("```")[1].split("```")[0].strip()

    if out:
        out.write_text(result)
        console.print(f"Saved to {out}")
    else:
        try:
            parsed = json.loads(result)
            console.print_json(json.dumps(parsed, indent=2))
        except Exception:
            console.print(result)


@app.command()
def index(
    folder: Path,
    out: Path = typer.Option(Path("research.index"), "--out"),
) -> None:
    """Build a semantic search index from a folder of PDFs."""
    pdfs = list(folder.glob("**/*.pdf"))
    if not pdfs:
        console.print("[red]No PDFs found[/red]")
        raise typer.Exit(1)

    console.print(f"Indexing {len(pdfs)} PDFs...")
    index_data = []

    for pdf in track(pdfs, description="Building index..."):
        try:
            text = _extract_text(pdf)
            chunks = _chunk(text)
            for i, chunk in enumerate(chunks[:20]):  # max 20 chunks per paper
                vec = _embed(chunk)
                index_data.append({
                    "source": pdf.name,
                    "chunk_id": i,
                    "text": chunk,
                    "embedding": vec,
                })
        except Exception as e:
            console.print(f"[yellow]Warning: {pdf.name} failed — {e}[/yellow]")

    with open(out, "wb") as f:
        pickle.dump(index_data, f)
    console.print(f"[green]Index built:[/green] {len(index_data)} chunks from {len(pdfs)} papers → {out}")


@app.command()
def search(
    query: str,
    index_file: Path = typer.Option(Path("research.index"), "--index"),
    top: int = typer.Option(5, "--top", "-n"),
) -> None:
    """Semantic search across indexed papers."""
    if not index_file.exists():
        console.print(f"[red]Index not found: {index_file}. Run 'index <folder>' first.[/red]")
        raise typer.Exit(1)

    with open(index_file, "rb") as f:
        index_data = pickle.load(f)

    query_vec = np.array(_embed(query))
    scores = []
    for item in index_data:
        vec = np.array(item["embedding"])
        score = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-9))
        scores.append((score, item))

    scores.sort(key=lambda x: x[0], reverse=True)
    console.print(f"\n[bold]Top {top} results for:[/bold] \"{query}\"\n")
    for score, item in scores[:top]:
        console.print(f"[cyan]{item['source']}[/cyan] [dim](score: {score:.3f})[/dim]")
        console.print(f"  {item['text'][:200]}...\n")


@app.command()
def cluster(
    folder: Path,
    themes: int = typer.Option(5, "--themes", "-t", help="Number of themes to find"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Find major themes across a folder of research papers."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import normalize

    pdfs = list(folder.glob("**/*.pdf"))
    console.print(f"Clustering {len(pdfs)} papers into {themes} themes...")

    all_chunks = []
    for pdf in track(pdfs, description="Reading papers..."):
        try:
            text = _extract_text(pdf)
            chunks = _chunk(text, size=300)[:10]
            for chunk in chunks:
                all_chunks.append({"source": pdf.name, "text": chunk})
        except Exception as e:
            console.print(f"[yellow]{pdf.name}: {e}[/yellow]")

    console.print(f"Embedding {len(all_chunks)} chunks...")
    vecs = []
    for item in track(all_chunks, description="Embedding..."):
        item["embedding"] = _embed(item["text"])
        vecs.append(item["embedding"])

    X = normalize(np.array(vecs))
    km = KMeans(n_clusters=themes, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    # Collect representative chunks per cluster
    clusters: dict[int, list[str]] = {i: [] for i in range(themes)}
    for idx, label in enumerate(labels):
        clusters[label].append(all_chunks[idx]["text"])

    # Name each cluster with Ollama
    result_lines = [f"# Literature Themes ({themes} clusters from {len(pdfs)} papers)\n"]
    for cluster_id, texts in clusters.items():
        sample = " ".join(texts[:3])[:1500]
        name_prompt = f"In 5 words or less, name the design research theme represented by these excerpts:\n{sample}"
        theme_name = _ask(name_prompt, "llama3.2:3b").strip().strip('"').strip("'")
        result_lines.append(f"## Theme {cluster_id + 1}: {theme_name}")
        result_lines.append(f"*{len(texts)} passages*\n")
        # Top 2 representative quotes
        for text in texts[:2]:
            result_lines.append(f"> {text[:200]}...")
        result_lines.append("")

    output = "\n".join(result_lines)
    if out:
        out.write_text(output)
        console.print(f"Themes saved to {out}")
    else:
        console.print(output)


@app.command()
def brief(
    folder: Path,
    project: str = typer.Option("", "--project", help="Project name or context"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Generate a design brief synthesizing insights from a literature folder."""
    pdfs = list(folder.glob("**/*.pdf"))
    summaries = []
    for pdf in track(pdfs[:8], description="Reading papers..."):
        try:
            text = _extract_text(pdf)[:3000]
            summaries.append(f"--- {pdf.name} ---\n{text}")
        except Exception:
            pass

    combined = "\n\n".join(summaries)
    context = f"Project context: {project}\n\n" if project else ""
    prompt = f"""{context}Based on the following research literature, generate a structured design brief for an Industrial Design project.

Include:
1. **Design Challenge** — the core problem to solve
2. **User Needs** — what users actually need (from the research)
3. **Design Principles** — 4-6 guiding principles derived from the literature
4. **Constraints & Opportunities** — technical, social, material
5. **Key Research Insights** — the 5 most actionable findings
6. **Open Questions** — what still needs primary research

Research:
{combined[:6000]}"""

    result = _ask(prompt, REASON_MODEL)
    if out:
        out.write_text(result)
        console.print(f"Brief saved to {out}")
    else:
        console.print(Panel(result, title="[bold]Design Brief from Literature[/bold]", border_style="green"))


if __name__ == "__main__":
    app()
