#!/usr/bin/env python3
"""
KB Clipper — Native Messaging Host
====================================
Chrome communicates with this process via stdin/stdout using the
Chrome Native Messaging protocol (4-byte length prefix + JSON).

This host reads ~/.kbconfig.json to find the KB paths and writes
clipped files directly to the appropriate raw/ directory.
"""

import json
import os
import re
import struct
import sys
import logging
from datetime import datetime
from pathlib import Path

# Log to a file (stdout is reserved for the messaging protocol)
LOG_PATH = Path.home() / ".kb_clipper.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("kb_clipper")

CONFIG_PATH = Path.home() / ".kbconfig.json"
VERSION = "1.0.0"


# ─── Chrome Native Messaging Protocol ────────────────────────────────────────

def read_message():
    """Read a message from Chrome (4-byte LE length prefix + JSON)."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    length = struct.unpack("<I", raw_length)[0]
    raw = sys.stdin.buffer.read(length)
    return json.loads(raw.decode("utf-8"))


def send_message(message: dict):
    """Send a message to Chrome."""
    encoded = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


# ─── Handlers ─────────────────────────────────────────────────────────────────

def handle_ping(cfg: dict) -> dict:
    personal_path = cfg.get("personal_kb_path", "")
    work_path = cfg.get("work_kb_path", "")
    return {
        "pong": True,
        "version": VERSION,
        "personalPath": personal_path,
        "workPath": work_path,
    }


def handle_save(message: dict, cfg: dict) -> dict:
    kb = message.get("kb", "personal")
    filename = message.get("filename", "")
    content = message.get("content", "")
    domain = message.get("domain", "misc/reference")

    if not filename or not content:
        return {"success": False, "error": "Missing filename or content"}

    # Get KB path
    key = f"{kb}_kb_path"
    kb_path_str = cfg.get(key, "")
    if not kb_path_str:
        return {"success": False, "error": f"No path configured for '{kb}' KB. Run 'kb setup' first."}

    kb_path = Path(kb_path_str).expanduser()
    raw_dir = kb_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_filename = re.sub(r"[^\w\-.]", "-", filename)
    if not safe_filename.endswith(".md"):
        safe_filename += ".md"

    # Avoid overwrites — add timestamp if file exists
    dest = raw_dir / safe_filename
    if dest.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = raw_dir / f"{dest.stem}-{ts}.md"

    try:
        dest.write_text(content, encoding="utf-8")
        log.info(f"Saved: {dest} (kb={kb}, domain={domain}, {len(content)} chars)")

        # Write sidecar metadata
        meta = {
            "kb": kb,
            "domain_override": domain if domain != "auto-detect" else None,
            "ingested": datetime.now().isoformat(),
            "source": "chrome-extension",
        }
        meta_path = dest.with_suffix(dest.suffix + ".meta.json")
        meta_path.write_text(json.dumps(meta, indent=2))

        return {"success": True, "path": str(dest)}

    except Exception as e:
        log.error(f"Failed to save {safe_filename}: {e}")
        return {"success": False, "error": str(e)}


# ─── Main Loop ────────────────────────────────────────────────────────────────

def main():
    log.info(f"KB Clipper native host started (v{VERSION})")
    cfg = load_config()
    log.info(f"Config loaded from {CONFIG_PATH}")

    while True:
        try:
            message = read_message()
            if message is None:
                log.info("stdin closed, exiting")
                break

            action = message.get("action")
            log.info(f"Received action: {action}")

            if action == "ping":
                send_message(handle_ping(cfg))
            elif action == "save":
                send_message(handle_save(message, cfg))
            else:
                send_message({"error": f"Unknown action: {action}"})

        except EOFError:
            log.info("EOF, exiting")
            break
        except Exception as e:
            log.error(f"Unexpected error: {e}", exc_info=True)
            try:
                send_message({"success": False, "error": str(e)})
            except Exception:
                break


if __name__ == "__main__":
    main()
