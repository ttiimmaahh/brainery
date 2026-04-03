#!/usr/bin/env bash
# ============================================================
#  Brainery uninstaller
#
#  Usage:
#    curl -fsSL https://raw.githubusercontent.com/ttiimmaahh/brainery/main/scripts/uninstall.sh | bash
#
#  Or run locally:
#    bash scripts/uninstall.sh
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
header()  { echo -e "\n${BOLD}$*${NC}"; }

echo ""
echo -e "  ${BOLD}Brainery Uninstaller${NC}"
echo -e "  ${DIM}This will remove the Brainery CLI and optionally its config files.${NC}"
echo -e "  ${DIM}Your KB data (articles, wiki) will NOT be deleted unless you choose.${NC}"
echo ""

# ── Confirm ───────────────────────────────────────────────────────────────────
read -r -p "  Continue with uninstall? [y/N] " CONFIRM </dev/tty
CONFIRM="${CONFIRM:-N}"
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo ""
  info "Uninstall cancelled."
  echo ""
  exit 0
fi

# ── Stop background services ─────────────────────────────────────────────────
header "Stopping Background Services"

# macOS launchd
for SVC_PLIST in "com.brainery.serve" "com.brainery.watch"; do
  PLIST="$HOME/Library/LaunchAgents/${SVC_PLIST}.plist"
  if [[ -f "$PLIST" ]]; then
    launchctl unload "$PLIST" 2>/dev/null
    rm -f "$PLIST"
    success "Removed $SVC_PLIST"
  fi
done

# Linux systemd
for SVC_UNIT in "brainery-serve" "brainery-watch"; do
  UNIT="$HOME/.config/systemd/user/${SVC_UNIT}.service"
  if [[ -f "$UNIT" ]]; then
    systemctl --user stop "$SVC_UNIT" 2>/dev/null
    systemctl --user disable "$SVC_UNIT" 2>/dev/null
    rm -f "$UNIT"
    success "Removed $SVC_UNIT"
  fi
done
# Reload systemd if any units were removed
if [[ -d "$HOME/.config/systemd/user" ]]; then
  systemctl --user daemon-reload 2>/dev/null || true
fi

# ── Remove CLI ────────────────────────────────────────────────────────────────
header "Removing Brainery CLI"

REMOVED=false

# Try uv first
if command -v uv &>/dev/null && uv tool list 2>/dev/null | grep -q "^brainery"; then
  info "Uninstalling via uv..."
  uv tool uninstall brainery
  success "Removed brainery (uv)"
  REMOVED=true
fi

# Try pip (may have been installed with --user or system pip)
if ! $REMOVED; then
  for PYTHON in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$PYTHON" &>/dev/null; then
      if "$PYTHON" -m pip show brainery &>/dev/null 2>&1; then
        info "Uninstalling via pip ($PYTHON)..."
        "$PYTHON" -m pip uninstall brainery -y -q \
          || "$PYTHON" -m pip uninstall brainery -y -q --break-system-packages 2>/dev/null \
          || true
        success "Removed brainery (pip)"
        REMOVED=true
        break
      fi
    fi
  done
fi

if ! $REMOVED; then
  warn "brainery not found via uv or pip — may already be uninstalled."
fi

# Remove 'kb' symlink if it points to brainery
if [[ -L "$(command -v kb 2>/dev/null)" ]]; then
  KB_TARGET=$(readlink "$(command -v kb)")
  if [[ "$KB_TARGET" == *brainery* ]]; then
    rm -f "$(command -v kb)" 2>/dev/null \
      && success "Removed 'kb' symlink" \
      || warn "Could not remove 'kb' symlink — remove manually: rm $(command -v kb)"
  fi
fi

# ── Config files ──────────────────────────────────────────────────────────────
header "Config files"

CONFIG_FILE="$HOME/.kbconfig.json"
BRAINERY_DIR="$HOME/.brainery"
PROMPTS_DIR="$BRAINERY_DIR/prompts"

if [[ -f "$CONFIG_FILE" ]]; then
  read -r -p "  Remove config file ($CONFIG_FILE)? [y/N] " RM_CFG </dev/tty
  RM_CFG="${RM_CFG:-N}"
  if [[ "$RM_CFG" =~ ^[Yy]$ ]]; then
    rm -f "$CONFIG_FILE"
    success "Removed $CONFIG_FILE"
  else
    info "Kept $CONFIG_FILE"
  fi
fi

if [[ -d "$PROMPTS_DIR" ]]; then
  read -r -p "  Remove prompts directory ($PROMPTS_DIR)? [y/N] " RM_PROMPTS </dev/tty
  RM_PROMPTS="${RM_PROMPTS:-N}"
  if [[ "$RM_PROMPTS" =~ ^[Yy]$ ]]; then
    rm -rf "$PROMPTS_DIR"
    success "Removed $PROMPTS_DIR"
  else
    info "Kept $PROMPTS_DIR"
  fi
fi

# Clean up daemon files if present
for f in "$BRAINERY_DIR/watch.pid" "$BRAINERY_DIR/watch.log"; do
  [[ -f "$f" ]] && rm -f "$f" && info "Removed $f"
done

# ── KB data ───────────────────────────────────────────────────────────────────
# Load KB paths from config (before we may have deleted it)
PERSONAL_KB=""
WORK_KB=""
if [[ -f "$CONFIG_FILE" ]] && command -v python3 &>/dev/null; then
  PERSONAL_KB=$(python3 -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('personal_kb_path',''))" 2>/dev/null || true)
  WORK_KB=$(python3 -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('work_kb_path',''))" 2>/dev/null || true)
fi

# Expand tildes
PERSONAL_KB="${PERSONAL_KB/#\~/$HOME}"
WORK_KB="${WORK_KB/#\~/$HOME}"

KB_DIRS=()
[[ -n "$PERSONAL_KB" && -d "$PERSONAL_KB" ]] && KB_DIRS+=("$PERSONAL_KB")
[[ -n "$WORK_KB" && -d "$WORK_KB" ]] && KB_DIRS+=("$WORK_KB")
# Also check the default location
[[ -d "$BRAINERY_DIR/personal" ]] && [[ "$BRAINERY_DIR/personal" != "$PERSONAL_KB" ]] && KB_DIRS+=("$BRAINERY_DIR/personal")
[[ -d "$BRAINERY_DIR/work" ]] && [[ "$BRAINERY_DIR/work" != "$WORK_KB" ]] && KB_DIRS+=("$BRAINERY_DIR/work")

if [[ ${#KB_DIRS[@]} -gt 0 ]]; then
  header "KB data"
  echo ""
  warn "The following directories contain your KB articles and raw files:"
  for d in "${KB_DIRS[@]}"; do
    echo "    $d"
  done
  echo ""
  echo -e "  ${RED}${BOLD}These will be permanently deleted if you say yes.${NC}"
  read -r -p "  Delete KB data? [y/N] " RM_DATA </dev/tty
  RM_DATA="${RM_DATA:-N}"
  if [[ "$RM_DATA" =~ ^[Yy]$ ]]; then
    for d in "${KB_DIRS[@]}"; do
      rm -rf "$d"
      success "Removed $d"
    done
  else
    info "KB data kept — your articles are safe."
  fi
fi

# Clean up .brainery dir
if [[ -d "$BRAINERY_DIR" ]]; then
  # Remove logs and other generated files
  for f in "$BRAINERY_DIR/serve.log" "$HOME/.kb_clipper.log"; do
    [[ -f "$f" ]] && rm -f "$f" && info "Removed $f"
  done

  if [[ -z "$(ls -A "$BRAINERY_DIR" 2>/dev/null)" ]]; then
    rmdir "$BRAINERY_DIR"
    success "Removed empty $BRAINERY_DIR"
  else
    echo ""
    info "Remaining contents in $BRAINERY_DIR:"
    ls "$BRAINERY_DIR" | sed 's/^/    /'
    echo ""
    read -r -p "  Remove entire $BRAINERY_DIR directory? [y/N] " RM_DIR </dev/tty
    RM_DIR="${RM_DIR:-N}"
    if [[ "$RM_DIR" =~ ^[Yy]$ ]]; then
      rm -rf "$BRAINERY_DIR"
      success "Removed $BRAINERY_DIR"
    else
      info "Kept $BRAINERY_DIR"
    fi
  fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
header "Done!"
echo ""
echo -e "  Brainery has been removed."
echo ""
if $REMOVED; then
  echo -e "  ${DIM}To reinstall:${NC}"
  echo -e "  ${DIM}curl -fsSL https://raw.githubusercontent.com/ttiimmaahh/brainery/main/scripts/install.sh | bash${NC}"
fi
echo ""
