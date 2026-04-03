"""Brainery clip server — lightweight HTTP API for the Chrome extension.

Listens on 127.0.0.1:52337 (localhost only). No auth needed since it
never binds to external interfaces.

Endpoints:
    GET  /api/ping   → health check + KB paths
    POST /api/clip   → save clipped content to raw/
"""

from __future__ import annotations

import json
import logging
import re
import signal
from datetime import datetime
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 52337
HOST = "127.0.0.1"
VERSION = "1.0.0"

log = logging.getLogger("brainery.server")


class ClipHandler(BaseHTTPRequestHandler):
    """Handles clip requests from the Chrome extension."""

    def __init__(self, cfg: dict, *args, **kwargs):
        self.cfg = cfg
        super().__init__(*args, **kwargs)

    # ── CORS ─────────────────────────────────────────────────────────────────

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _json_response(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    # ── Routes ───────────────────────────────────────────────────────────────

    def do_GET(self):
        if self.path == "/api/ping":
            self._handle_ping()
        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/api/clip":
            self._handle_clip()
        else:
            self._json_response(404, {"error": "Not found"})

    def _handle_ping(self):
        self._json_response(200, {
            "pong": True,
            "version": VERSION,
            "personalPath": self.cfg.get("personal_kb_path", ""),
            "workPath": self.cfg.get("work_kb_path", ""),
        })

    def _handle_clip(self):
        body = self._read_json_body()
        if not body:
            self._json_response(400, {"success": False, "error": "Empty request body"})
            return

        result = save_clip(body, self.cfg)
        status = 200 if result["success"] else 400
        self._json_response(status, result)

    # ── Logging ──────────────────────────────────────────────────────────────

    def log_message(self, format, *args):
        log.info(format % args)


def save_clip(message: dict, cfg: dict) -> dict:
    """Save clipped content to the raw/ directory. Shared with native host."""
    kb = message.get("kb", "personal")
    filename = message.get("filename", "")
    content = message.get("content", "")
    domain = message.get("domain", "misc/reference")

    if not filename or not content:
        return {"success": False, "error": "Missing filename or content"}

    key = f"{kb}_kb_path"
    kb_path_str = cfg.get(key, "")
    if not kb_path_str:
        return {"success": False, "error": f"No path configured for '{kb}' KB. Run 'brainery setup' first."}

    kb_path = Path(kb_path_str).expanduser()
    raw_dir = kb_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_filename = re.sub(r"[^\w\-.]", "-", filename)
    if not safe_filename.endswith(".md"):
        safe_filename += ".md"

    # Avoid overwrites
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


def run(args, cfg):
    """Start the clip server, or manage the background service."""
    from brainery.service import install_service, is_running, uninstall_service

    # Handle --install / --uninstall / --status flags
    if getattr(args, "install", False):
        if install_service():
            print("Clip server will auto-start on login.")
        return

    if getattr(args, "uninstall", False):
        uninstall_service()
        return

    if getattr(args, "status", False):
        if is_running():
            print(f"Clip server: running (http://{HOST}:{PORT})")
        else:
            print("Clip server: not running")
            print("  Start it:     brainery serve")
            print("  Auto-start:   brainery serve --install")
        return

    # Foreground mode — start the server directly
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    handler = partial(ClipHandler, cfg)
    server = HTTPServer((HOST, PORT), handler)

    # Graceful shutdown
    def _shutdown(signum, frame):
        log.info("Shutting down...")
        server.shutdown()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    print(f"Brainery clip server running on http://{HOST}:{PORT}")
    print("  POST /api/clip  — save clipped content")
    print("  GET  /api/ping  — health check")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        log.info("Server stopped.")
