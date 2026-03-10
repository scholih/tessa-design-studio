#!/usr/bin/env bash
# Tessa Design Studio — full setup script
# Run once after cloning the repo
set -euo pipefail

echo "================================================"
echo "  Tessa Design Studio — Environment Setup"
echo "================================================"
echo ""

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. Homebrew ────────────────────────────────────
echo "→ Checking Homebrew..."
if ! command -v brew &>/dev/null; then
  echo "  Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo "  ✓ Homebrew ready"

# ── 2. Core tools ──────────────────────────────────
echo ""
echo "→ Installing core tools..."
brew install git gh uv ollama 2>/dev/null || true
brew services start ollama 2>/dev/null || true
echo "  ✓ git, gh, uv, ollama installed"

# ── 3. Claude Code ─────────────────────────────────
echo ""
echo "→ Installing Claude Code..."
if ! command -v claude &>/dev/null; then
  if ! command -v npm &>/dev/null; then
    brew install node
  fi
  npm install -g @anthropic-ai/claude-code
fi
echo "  ✓ Claude Code ready"

# ── 4. Python sidecar ─────────────────────────────
echo ""
echo "→ Installing Python sidecar tools..."
cd "$REPO_DIR/_sidecar"
uv sync
echo "  ✓ Sidecar installed"

# ── 5. Ollama models ──────────────────────────────
echo ""
echo "→ Pulling Ollama models (this takes a while first time)..."
echo "  These run locally on your Mac — private, no API cost."
echo ""

pull_model() {
  local model=$1
  local desc=$2
  if ollama list 2>/dev/null | grep -q "^${model%:*}"; then
    echo "  ✓ $model already present ($desc)"
  else
    echo "  ↓ Pulling $model ($desc)..."
    ollama pull "$model"
  fi
}

pull_model "llama3.2:3b"       "fast, for quick tasks"
pull_model "llama3.1:8b"       "default reasoning"
pull_model "nomic-embed-text"  "semantic search across your research"
pull_model "mistral:7b"        "structured extraction from interviews"
pull_model "llava:13b"         "image analysis for moodboards"

echo ""
echo "  Optional: for deep analysis (needs ~40GB RAM):"
echo "  ollama pull llama3.1:70b"

# ── 6. Beads ──────────────────────────────────────
echo ""
echo "→ Setting up beads task tracker..."
if ! command -v bd &>/dev/null; then
  echo "  Install beads from: https://github.com/tidewave-ai/beads"
  echo "  (Ask Claude to help you install it)"
else
  cd "$REPO_DIR"
  bd init 2>/dev/null || true
  echo "  ✓ Beads ready"
fi

# ── 7. Media folder ───────────────────────────────
echo ""
echo "→ Creating media folder (not in git, syncs to pCloud)..."
mkdir -p ~/Design/media/renders
mkdir -p ~/Design/media/videos
mkdir -p ~/Design/media/exports
mkdir -p ~/Design/media/assets
echo "  ✓ ~/Design/media/ ready"

# ── 8. CLAUDE.md ──────────────────────────────────
echo ""
echo "→ Copying CLAUDE.md to your global Claude config..."
mkdir -p ~/.claude
if [ ! -f ~/.claude/CLAUDE.md ]; then
  cp "$REPO_DIR/CLAUDE.md" ~/.claude/CLAUDE.md
  echo "  ✓ ~/.claude/CLAUDE.md created"
else
  echo "  [note] ~/.claude/CLAUDE.md already exists — not overwriting"
  echo "         Review $REPO_DIR/CLAUDE.md and merge manually if needed"
fi

# ── Done ──────────────────────────────────────────
echo ""
echo "================================================"
echo "  Setup complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Open this folder in Claude Code: claude ."
echo "  2. Tell Claude: 'I just finished setup, what should I do first?'"
echo "  3. Claude will create your first project and show you what's possible"
echo ""
echo "Your tools:"
echo "  Research:   uv run _sidecar/research.py --help"
echo "  Interviews: uv run _sidecar/cluster.py --help"
echo "  Video:      uv run _sidecar/video_prompt.py --help"
echo "  Moodboard:  uv run _sidecar/moodboard.py --help"
echo "  Figma:      uv run _sidecar/figma.py --help  (needs FIGMA_TOKEN)"
