# CLAUDE.md — Tessa's Design Studio

## Who I am
Tessa Scholing — Master student Industrial Design at Delft University of Technology.
I work on design research, concept development, prototyping, and design communication.
My father Hans set up this environment for me.

## My tools and when to use each

| Tool | When to use |
|------|------------|
| **Claude Code** (you) | Research synthesis, writing briefs, coding prototypes, everything in this repo |
| **Figma** | Visual design, wireframes, mockups, design systems |
| **Gemini** | Quick questions, image analysis, Google ecosystem tasks |
| **NotebookLM** | Deep-diving into a specific set of papers (upload PDFs there) |
| **Runway / Kling / Veo** | Video and motion generation for presentations |
| **Ollama** (local) | Semantic search, clustering interviews, analyzing research privately |
| **pCloud** | ALL large files — videos, renders, exports, high-res images |

## File rules (MANDATORY)

- **git repo = text only**: code, notes, briefs, configs, small SVGs, markdown
- **Never commit files > 500KB** — git will become unusable
- **All media → `~/Design/media/`** which syncs to pCloud
- **Link media in your notes**: "video at pCloud/projects/thesis/render_v3.mp4"

## My working style

- I'm a designer, not a developer — explain things visually and with analogies
- Use design terminology (affordance, prototype, iteration) not software jargon
- When I ask "how should I approach X", give me a design process, not just a technical answer
- Short, clear answers preferred — I can ask follow-up questions
- If something will take multiple steps, tell me the plan before starting

## My projects structure

```
~/Design/tessa-design-studio/     ← this repo
├── projects/
│   └── <project-name>/
│       ├── research/             ← papers, notes, transcripts
│       ├── briefs/               ← design briefs, requirements
│       ├── iterations/           ← design decisions log
│       └── README.md             ← project overview
├── research/                     ← general literature (cross-project)
└── _sidecar/                     ← Python tools

~/Design/media/                   ← NOT in git
├── renders/
├── videos/
├── exports/
└── assets/
```

## Python sidecar tools

Available tools for research and design tasks:

```bash
# Analyze research papers
uv run _sidecar/research.py summarize paper.pdf
uv run _sidecar/research.py cluster papers/ --themes 5
uv run _sidecar/research.py brief papers/ --project "my thesis topic"

# User research analysis
uv run _sidecar/cluster.py affinity interviews/
uv run _sidecar/cluster.py personas interviews/ --count 3
uv run _sidecar/cluster.py insights interviews/

# Figma (needs FIGMA_TOKEN env var)
uv run _sidecar/figma.py frames <file_key> --out exports/
uv run _sidecar/figma.py tokens <file_key>

# Video prompts
uv run _sidecar/video_prompt.py product "my product description"
uv run _sidecar/video_prompt.py scenario "user using the product"
uv run _sidecar/video_prompt.py sequence brief.md

# Moodboards
uv run _sidecar/moodboard.py collect urls.txt --out refs/
uv run _sidecar/moodboard.py grid refs/ --out moodboard.jpg
uv run _sidecar/moodboard.py palette refs/
uv run _sidecar/moodboard.py analyze refs/
```

## Beads (task tracking)

All project tasks tracked via beads (`bd`). Context survives between sessions.

```bash
bd ready              # what can I work on now?
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id>
```

## Session start

At the start of each session:
1. Run `bd dolt pull` and `bd ready`
2. Check what project I'm working on
3. Pick up where we left off
