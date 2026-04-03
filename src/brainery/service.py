"""Auto-start service management for the Brainery clip server.

macOS: ~/Library/LaunchAgents/com.brainery.serve.plist
Linux: ~/.config/systemd/user/brainery-serve.service
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

SERVICE_LABEL = "com.brainery.serve"
SYSTEMD_UNIT = "brainery-serve"


def install_service() -> bool:
    """Install and start the auto-start service. Returns True on success."""
    brainery_bin = _find_brainery_bin()
    if not brainery_bin:
        print("[error] Cannot find 'brainery' binary. Is it installed?")
        return False

    if platform.system() == "Darwin":
        return _install_launchd(brainery_bin)
    elif platform.system() == "Linux":
        return _install_systemd(brainery_bin)
    else:
        print(f"[warn] Auto-start not supported on {platform.system()}. Run 'brainery serve' manually.")
        return False


def uninstall_service() -> bool:
    """Stop and remove the auto-start service."""
    if platform.system() == "Darwin":
        return _uninstall_launchd()
    elif platform.system() == "Linux":
        return _uninstall_systemd()
    return False


def is_running() -> bool:
    """Check if the clip server service is currently running."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:52337/api/ping", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


# ── macOS (launchd) ──────────────────────────────────────────────────────────

def _launchd_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_LABEL}.plist"


def _install_launchd(brainery_bin: str) -> bool:
    plist_path = _launchd_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    log_path = Path.home() / ".brainery" / "serve.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{SERVICE_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{brainery_bin}</string>
        <string>serve</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""

    # Unload first if already loaded
    if plist_path.exists():
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True,
        )

    plist_path.write_text(plist_content)

    result = subprocess.run(
        ["launchctl", "load", str(plist_path)],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print(f"[error] launchctl load failed: {result.stderr.strip()}")
        return False

    print(f"  Service installed: {plist_path}")
    print(f"  Log: {log_path}")
    return True


def _uninstall_launchd() -> bool:
    plist_path = _launchd_plist_path()
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink()
        print(f"  Service removed: {plist_path}")
        return True
    print("  No launchd service found.")
    return False


# ── Linux (systemd) ──────────────────────────────────────────────────────────

def _systemd_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / f"{SYSTEMD_UNIT}.service"


def _install_systemd(brainery_bin: str) -> bool:
    unit_path = _systemd_unit_path()
    unit_path.parent.mkdir(parents=True, exist_ok=True)

    unit_content = f"""[Unit]
Description=Brainery Clip Server
After=network.target

[Service]
Type=simple
ExecStart={brainery_bin} serve
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""

    unit_path.write_text(unit_content)

    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", SYSTEMD_UNIT], capture_output=True)
    result = subprocess.run(
        ["systemctl", "--user", "start", SYSTEMD_UNIT],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print(f"[error] systemctl start failed: {result.stderr.strip()}")
        return False

    print(f"  Service installed: {unit_path}")
    return True


def _uninstall_systemd() -> bool:
    unit_path = _systemd_unit_path()
    if unit_path.exists():
        subprocess.run(["systemctl", "--user", "stop", SYSTEMD_UNIT], capture_output=True)
        subprocess.run(["systemctl", "--user", "disable", SYSTEMD_UNIT], capture_output=True)
        unit_path.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        print(f"  Service removed: {unit_path}")
        return True
    print("  No systemd service found.")
    return False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _find_brainery_bin() -> str | None:
    """Locate the brainery binary."""
    path = shutil.which("brainery")
    if path:
        return path
    # Fallback: same directory as current Python
    candidate = Path(sys.executable).parent / "brainery"
    if candidate.exists():
        return str(candidate)
    return None
