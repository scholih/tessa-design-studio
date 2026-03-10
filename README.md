# Tessa Design Studio

Your personal design research environment — AI-powered tools for Industrial Design at TU Delft.

## First time setup

```bash
./setup.sh
```

That's it. Takes ~10 minutes on first run (pulls AI models). Then:

```bash
claude .
```

Tell Claude: *"I just finished setup, what should I do first?"*

## What's here

```
tessa-design-studio/
├── projects/          ← one folder per project (thesis, studio, etc.)
├── research/          ← papers and literature that span multiple projects
└── _sidecar/          ← Python AI tools (don't edit unless you know what you're doing)
```

Large files (videos, renders, images) go to `~/Design/media/` which syncs to pCloud — never commit them here.

## AI tools

### Research
```bash
# Summarize a paper
uv run _sidecar/research.py summarize paper.pdf

# Find relevant papers on a topic
uv run _sidecar/research.py search papers/ "sustainable packaging materials"

# Generate a literature brief
uv run _sidecar/research.py brief papers/ --project "my thesis topic"
```

### User research
```bash
# Cluster interview transcripts into themes
uv run _sidecar/cluster.py affinity interviews/

# Generate personas from interviews
uv run _sidecar/cluster.py personas interviews/ --count 3

# Extract "How Might We" statements
uv run _sidecar/cluster.py insights interviews/
```

### Moodboards
```bash
# Download reference images from a list of URLs
uv run _sidecar/moodboard.py collect urls.txt --out refs/

# Compose into a grid
uv run _sidecar/moodboard.py grid refs/ --out moodboard.jpg

# Extract color palette
uv run _sidecar/moodboard.py palette refs/
```

### Video prompts (for Runway / Kling / Veo)
```bash
# Product showcase prompt
uv run _sidecar/video_prompt.py product "ergonomic water bottle" --style minimal

# User scenario prompt
uv run _sidecar/video_prompt.py scenario "person unpacking sustainable packaging"

# Generate a full shot list from a brief
uv run _sidecar/video_prompt.py sequence brief.md
```

### Figma (needs FIGMA_TOKEN)
```bash
export FIGMA_TOKEN=your_token_here

# Export all frames from a file
uv run _sidecar/figma.py frames <file_key> --out exports/

# Extract design tokens
uv run _sidecar/figma.py tokens <file_key>
```

## Project structure (recommended)

```
projects/
└── thesis-2025/
    ├── README.md          ← what this project is about
    ├── research/          ← papers, notes, transcripts
    ├── briefs/            ← design briefs, requirements
    └── iterations/        ← design decisions log
```

## Rules

- **Never commit files > 500KB** — git breaks and becomes unusable
- **All media → `~/Design/media/`** which syncs to pCloud
- **Reference media in your notes**: `video at pCloud/projects/thesis/render_v3.mp4`
