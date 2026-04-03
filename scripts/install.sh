#!/usr/bin/env bash
# ============================================================
#  Brainery installer
#  A brewery for your brain — LLM-powered knowledge base CLI
#
#  Usage (recommended):
#    curl -fsSL https://raw.githubusercontent.com/timpearsoncx/brainery/main/scripts/install.sh | bash
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
PACKAGE="brainery"

if [[ -n "$VERSION" ]]; then
  PACKAGE="brainery==$VERSION"
  info "Pinned version: $VERSION"
fi

# Detect if we should use --user (no write access to site-packages)
PIP_FLAGS=""
if [[ ! -w "$("$PYTHON" -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || echo '')" ]]; then
  PIP_FLAGS="--user"
  warn "No write access to system site-packages — installing with --user"
fi

info "Installing $PACKAGE..."
"$PYTHON" -m pip install $PIP_FLAGS --upgrade "$PACKAGE" -q \
  || die "pip install failed. Try: $PYTHON -m pip install brainery"

success "Brainery installed"

# ── PATH check ────────────────────────────────────────────────────────────────
header "PATH configuration"

KB_PATH=$("$PYTHON" -m pip show -f brainery 2>/dev/null \
  | grep "^Location:" | awk '{print $2}' || true)

SCRIPTS_DIR=""
if [[ "$PIP_FLAGS" == "--user" ]]; then
  SCRIPTS_DIR=$("$PYTHON" -m site --user-base)/bin
else
  SCRIPTS_DIR=$(dirname "$("$PYTHON" -c "import sys; print(sys.executable)")")
fi

PATH_OK=false
if command -v kb &>/dev/null; then
  PATH_OK=true
  success "'kb' command found at $(command -v kb)"
else
  warn "'kb' not found on PATH."
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
    read -r -p "  Add it automatically now? [Y/n] " ADD_PATH
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
  echo -e "  Run ${BOLD}kb setup${NC} to configure your knowledge base paths and LLM backend."
  echo ""
  read -r -p "  Run 'kb setup' now? [Y/n] " RUN_SETUP
  RUN_SETUP="${RUN_SETUP:-Y}"
  if [[ "$RUN_SETUP" =~ ^[Yy]$ ]]; then
    echo ""
    kb setup
  fi
fi

echo ""
echo -e "  ${DIM}Docs: https://github.com/timpearsoncx/brainery${NC}"
echo -e "  ${DIM}Give it a star if it helps you! ⭐${NC}"
echo ""
