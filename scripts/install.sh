#!/usr/bin/env bash
# ============================================================
#  Brainery installer
#  A brewery for your brain — LLM-powered knowledge base CLI
#
#  Usage (recommended):
#    curl -fsSL https://raw.githubusercontent.com/ttiimmaahh/brainery/main/scripts/install.sh | bash
#
#  Or clone and run locally:
#    bash scripts/install.sh
#
#  Options (env vars):
#    BRAINERY_VERSION   Pin a release, e.g. BRAINERY_VERSION=0.2.0
#    BRAINERY_NO_SETUP  Skip the post-install setup prompt
#    BRAINERY_PREFIX    Install prefix (default: /usr/local or ~/bin)
# ============================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
  BLUE='\033[0;34m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; DIM=''; NC=''
fi

info()    { echo -e "  ${BLUE}•${NC} $*"; }
success() { echo -e "  ${GREEN}✓${NC} $*"; }
warn()    { echo -e "  ${YELLOW}!${NC} $*"; }
error()   { echo -e "  ${RED}✗${NC} $*" >&2; }
die()     { error "$*"; exit 1; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}${BOLD}"
echo "  ██████╗ ██████╗  █████╗ ██╗███╗   ██╗███████╗██████╗ ██╗   ██╗"
echo "  ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝██╔══██╗╚██╗ ██╔╝"
echo "  ██████╔╝██████╔╝███████║██║██╔██╗ ██║█████╗  ██████╔╝ ╚████╔╝ "
echo "  ██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║██╔══╝  ██╔══██╗  ╚██╔╝  "
echo "  ██████╔╝██║  ██║██║  ██║██║██║ ╚████║███████╗██║  ██║   ██║   "
echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝   ╚═╝   "
echo -e "${NC}"
echo -e "  ${DIM}A brewery for your brain — LLM-powered knowledge base${NC}"
echo ""

# ── OS detection ─────────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Darwin) PLATFORM="macOS ($ARCH)" ;;
  Linux)  PLATFORM="Linux ($ARCH)" ;;
  *)      die "Unsupported OS: $OS. Windows support coming soon — see README." ;;
esac

header "System"
info "Platform: $PLATFORM"

# ── Python check ─────────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$candidate" &>/dev/null; then
    version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  error "Python 3.10+ is required but not found."
  echo ""
  if [[ "$OS" == "Darwin" ]]; then
    echo "  Install with Homebrew:  brew install python@3.12"
    echo "  Or download from:       https://www.python.org/downloads/"
  else
    echo "  Ubuntu/Debian:  sudo apt install python3.12"
    echo "  Fedora:         sudo dnf install python3.12"
    echo "  Or download:    https://www.python.org/downloads/"
  fi
  echo ""
  exit 1
fi

success "Python $("$PYTHON" -c "import sys; print(sys.version.split()[0])")"

# ── pip check ─────────────────────────────────────────────────────────────────
if ! "$PYTHON" -m pip --version &>/dev/null; then
  warn "pip not found — attempting to bootstrap it..."
  "$PYTHON" -m ensurepip --upgrade 2>/dev/null || die "Could not install pip. Install it manually and re-run."
fi

success "pip $("$PYTHON" -m pip --version | awk '{print $2}')"

# ── Install Brainery ──────────────────────────────────────────────────────────
header "Installing Brainery"

VERSION="${BRAINERY_VERSION:-}"
BRAINERY_LOCAL="${BRAINERY_LOCAL:-}"   # dev only: set to local repo path

# Resolve what to install
GITHUB_URL="git+https://github.com/ttiimmaahh/brainery.git"

if [[ -n "$BRAINERY_LOCAL" ]]; then
  PACKAGE="$BRAINERY_LOCAL"
  info "Local install from: $PACKAGE"
elif [[ -n "$VERSION" ]]; then
  PACKAGE="brainery==$VERSION"
  info "Installing version: $VERSION"
else
  PACKAGE="brainery"
fi

# ── Detect installer ──────────────────────────────────────────────────────────
# Prefer uv — handles externally-managed Python environments (common on macOS)
# Fall back to pip with --user or --break-system-packages as needed

_do_install() {
  local pkg="$1"
  if command -v uv &>/dev/null; then
    info "Using uv (detected)"
    # uv tool install: installs kb as an isolated tool into ~/.local/bin
    uv tool install "$pkg" 2>/dev/null && return 0
    # fallback: uv pip into the active env
    uv pip install "$pkg" 2>/dev/null && return 0
    return 1
  else
    # Try plain pip first
    "$PYTHON" -m pip install --upgrade "$pkg" -q 2>/dev/null && return 0
    # Externally-managed env? Try --user
    "$PYTHON" -m pip install --user --upgrade "$pkg" -q 2>/dev/null && return 0
    # Last resort for system Pythons that block everything
    "$PYTHON" -m pip install --break-system-packages --upgrade "$pkg" -q 2>/dev/null && return 0
    return 1
  fi
}

info "Installing $PACKAGE..."

# Try PyPI first; if not found (pre-release), fall back to GitHub
if ! _do_install "$PACKAGE"; then
  if [[ "$PACKAGE" == "brainery" ]]; then
    warn "Not on PyPI yet — installing from GitHub..."
    _do_install "$GITHUB_URL" \
      || die "Installation failed. Please open an issue: https://github.com/ttiimmaahh/brainery/issues"
  else
    die "Installation failed. Try manually: uv tool install brainery"
  fi
fi

# Detect whether uv tool install was used (kb lands in ~/.local/bin)
INSTALLED_WITH_UV=false
if command -v uv &>/dev/null; then
  INSTALLED_WITH_UV=true
fi

success "Brainery installed"

# ── Create 'kb' shorthand alias ──────────────────────────────────────────────
# The package only ships the 'brainery' binary; 'kb' is a convenience symlink.
if command -v brainery &>/dev/null; then
  BRAINERY_BIN="$(command -v brainery)"
  KB_LINK="$(dirname "$BRAINERY_BIN")/kb"
  if [[ ! -e "$KB_LINK" ]]; then
    ln -sf "$BRAINERY_BIN" "$KB_LINK" 2>/dev/null \
      && success "'kb' alias created → $KB_LINK" \
      || warn "Could not create 'kb' symlink (try: sudo ln -sf $BRAINERY_BIN $KB_LINK)"
  else
    success "'kb' alias already exists at $KB_LINK"
  fi
fi

# ── Detect local LLM backends ────────────────────────────────────────────────
header "LLM Backend Detection"

LLM_FOUND=0

# Ollama
if command -v ollama &>/dev/null; then
  OLLAMA_MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | head -5 | tr '\n' ', ' | sed 's/,$//')
  if [[ -n "$OLLAMA_MODELS" ]]; then
    success "Ollama — models: $OLLAMA_MODELS"
  else
    success "Ollama — installed (no models pulled yet)"
    info "  Pull a model: ollama pull llama3"
  fi
  LLM_FOUND=$((LLM_FOUND + 1))
else
  info "Ollama — not found (https://ollama.com)"
fi

# LM Studio (check if server is running)
if curl -sf http://localhost:1234/v1/models >/dev/null 2>&1; then
  success "LM Studio — server running on :1234"
  LLM_FOUND=$((LLM_FOUND + 1))
else
  info "LM Studio — server not detected on :1234"
fi

# GGUF models (quick scan)
GGUF_COUNT=0
for search_dir in \
  "$HOME/.lmstudio/models" \
  "$HOME/Library/Application Support/LM Studio/Models" \
  "$HOME/jan/models" \
  "$HOME/models" \
  "$HOME/.local/share/models"; do
  if [[ -d "$search_dir" ]]; then
    count=$(find "$search_dir" -name '*.gguf' -maxdepth 4 2>/dev/null | head -10 | wc -l | tr -d ' ')
    GGUF_COUNT=$((GGUF_COUNT + count))
  fi
done

if [[ "$GGUF_COUNT" -gt 0 ]]; then
  success "llama-cpp — $GGUF_COUNT .gguf model(s) found locally"
  LLM_FOUND=$((LLM_FOUND + 1))
else
  info "llama-cpp — no .gguf models found"
fi

# Anthropic
info "Anthropic API — always available (requires API key)"

if [[ "$LLM_FOUND" -eq 0 ]]; then
  echo ""
  warn "No local LLM backends detected."
  info "  For local/offline use, install one of:"
  info "    Ollama:     https://ollama.com"
  info "    LM Studio:  https://lmstudio.ai"
  info "  Or use the Anthropic API (cloud, requires API key)."
fi

# ── PATH check ────────────────────────────────────────────────────────────────
header "PATH configuration"

SCRIPTS_DIR=""
if [[ "$INSTALLED_WITH_UV" == "true" ]]; then
  SCRIPTS_DIR="$HOME/.local/bin"
elif [[ "$PIP_FLAGS" == "--user" ]]; then
  SCRIPTS_DIR=$("$PYTHON" -m site --user-base)/bin
else
  SCRIPTS_DIR=$(dirname "$("$PYTHON" -c "import sys; print(sys.executable)")")
fi

PATH_OK=false
if command -v brainery &>/dev/null; then
  PATH_OK=true
  success "'brainery' command found at $(command -v brainery)"
else
  warn "'brainery' not found on PATH."
  info "Scripts directory: ${SCRIPTS_DIR}"
  echo ""
  SHELL_RC=""
  if [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
  elif [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bash_profile"
  fi

  if [[ -n "$SHELL_RC" ]]; then
    echo -e "  Add this to ${BOLD}${SHELL_RC}${NC} then restart your terminal:"
    echo ""
    echo -e "    ${YELLOW}export PATH=\"${SCRIPTS_DIR}:\$PATH\"${NC}"
    echo ""
    read -r -p "  Add it automatically now? [Y/n] " ADD_PATH </dev/tty
    ADD_PATH="${ADD_PATH:-Y}"
    if [[ "$ADD_PATH" =~ ^[Yy]$ ]]; then
      echo "" >> "$SHELL_RC"
      echo "# Brainery" >> "$SHELL_RC"
      echo "export PATH=\"${SCRIPTS_DIR}:\$PATH\"" >> "$SHELL_RC"
      export PATH="${SCRIPTS_DIR}:$PATH"
      success "Added to $SHELL_RC"
      PATH_OK=true
    fi
  fi
fi

# ── Post-install ──────────────────────────────────────────────────────────────
header "Done!"
echo ""
echo -e "  ${GREEN}${BOLD}Brainery is installed.${NC}"
echo ""

if [[ -z "${BRAINERY_NO_SETUP:-}" ]]; then
  echo -e "  Run ${BOLD}brainery setup${NC} to configure your knowledge base paths and LLM backend."
  echo -e "  ${DIM}(Tip: 'kb' is a shorthand alias for 'brainery')${NC}"
  echo ""
  read -r -p "  Run 'brainery setup' now? [Y/n] " RUN_SETUP </dev/tty
  RUN_SETUP="${RUN_SETUP:-Y}"
  if [[ "$RUN_SETUP" =~ ^[Yy]$ ]]; then
    echo ""
    brainery setup </dev/tty
  fi
fi

# ── Background services ──────────────────────────────────────────────────────
header "Background Services"

echo -e "  Brainery can run two background services that auto-start on login:"
echo -e "    ${BOLD}Clip server${NC}  — lets the Chrome extension send clips (port 52337)"
echo -e "    ${BOLD}Watch daemon${NC} — auto-compiles new files as they arrive in raw/"
echo ""

read -r -p "  Start clip server on login? [Y/n] " START_SERVER </dev/tty
START_SERVER="${START_SERVER:-Y}"
if [[ "$START_SERVER" =~ ^[Yy]$ ]]; then
  brainery serve --install 2>/dev/null \
    && success "Clip server installed" \
    || warn "Could not start clip server. Run: brainery serve --install"
fi

read -r -p "  Start watch daemon on login? [Y/n] " START_WATCH </dev/tty
START_WATCH="${START_WATCH:-Y}"
if [[ "$START_WATCH" =~ ^[Yy]$ ]]; then
  brainery watch --install 2>/dev/null \
    && success "Watch daemon installed" \
    || warn "Could not start watch daemon. Run: brainery watch --install"
fi

echo ""
echo -e "  ${DIM}Docs: https://github.com/ttiimmaahh/brainery${NC}"
echo -e "  ${DIM}Give it a star if it helps you! ⭐${NC}"
echo ""
