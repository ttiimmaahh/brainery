#!/usr/bin/env bash
# install_host.sh — Install the KB Clipper native messaging host
#
# Usage:
#   bash install_host.sh <extension-id>
#
# Find your extension ID at chrome://extensions after loading the extension.
# You only need to run this once (or again if you move the files).

set -e

EXTENSION_ID="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_SCRIPT="$SCRIPT_DIR/kb_clipper.py"
MANIFEST_TEMPLATE="$SCRIPT_DIR/com.kb.clipper.json"

echo ""
echo "=== KB Clipper — Native Host Installer ==="
echo ""

if [ -z "$EXTENSION_ID" ]; then
  echo "Usage: bash install_host.sh <extension-id>"
  echo ""
  echo "Find your extension ID:"
  echo "  1. Open Chrome → chrome://extensions"
  echo "  2. Enable Developer mode (toggle top right)"
  echo "  3. Find 'KB Clipper' and copy the ID shown below the name"
  echo ""
  exit 1
fi

# Validate it looks like an extension ID
if ! echo "$EXTENSION_ID" | grep -qE "^[a-z]{32}$"; then
  echo "[warn] '$EXTENSION_ID' doesn't look like a Chrome extension ID (32 lowercase letters)."
  echo "       Proceeding anyway — double-check if it doesn't work."
  echo ""
fi

# Make host script executable
chmod +x "$HOST_SCRIPT"

# Verify Python 3 is available at a usable path
PYTHON_PATH=$(which python3 || which python)
if [ -z "$PYTHON_PATH" ]; then
  echo "[error] Python 3 not found. Please install Python 3 first."
  exit 1
fi

# Rewrite shebang to use the actual python3 path
sed -i.bak "s|#!/usr/bin/env python3|#!$PYTHON_PATH|" "$HOST_SCRIPT" 2>/dev/null || true

# Determine native messaging hosts directory
OS=$(uname -s)
if [ "$OS" = "Darwin" ]; then
  CHROME_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
  BRAVE_DIR="$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
  ARC_DIR="$HOME/Library/Application Support/Arc/User Data/NativeMessagingHosts"
elif [ "$OS" = "Linux" ]; then
  CHROME_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
  BRAVE_DIR="$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
  ARC_DIR=""
else
  echo "[error] Windows is not supported by this script. See Chrome docs for manual installation."
  exit 1
fi

# Generate the manifest
MANIFEST_CONTENT=$(cat <<EOF
{
  "name": "com.kb.clipper",
  "description": "KB Clipper native messaging host",
  "path": "$HOST_SCRIPT",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$EXTENSION_ID/"
  ]
}
EOF
)

MANIFEST_FILENAME="com.kb.clipper.json"

install_for_browser() {
  local dir="$1"
  local name="$2"
  if [ -d "$(dirname "$dir")" ]; then
    mkdir -p "$dir"
    echo "$MANIFEST_CONTENT" > "$dir/$MANIFEST_FILENAME"
    echo "  ✓ Installed for $name → $dir/$MANIFEST_FILENAME"
  fi
}

install_for_browser "$CHROME_DIR" "Chrome"
install_for_browser "$BRAVE_DIR" "Brave"
[ -n "$ARC_DIR" ] && install_for_browser "$ARC_DIR" "Arc"

echo ""
echo "  Extension ID: $EXTENSION_ID"
echo "  Host script:  $HOST_SCRIPT"
echo ""
echo "  Next steps:"
echo "  1. Reload the KB Clipper extension in chrome://extensions"
echo "  2. Click the extension icon — the dot should turn green (connected)"
echo "  3. Make sure 'kb setup' has been run to configure KB paths"
echo ""
echo "  Log file: ~/.kb_clipper.log"
echo ""
