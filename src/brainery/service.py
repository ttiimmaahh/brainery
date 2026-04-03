"""Auto-start service management for Brainery background processes.

Supports two services:
  - serve: HTTP clip server for Chrome extension (port 52337)
  - watch: auto-compile daemon that watches raw/ for new files

macOS: ~/Library/LaunchAgents/com.brainery.{name}.plist
Linux: ~/.config/systemd/user/brainery-{name}.service
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Service definitions: name -> (label, description, args)
SERVICES = {
    "serve": {
        "label": "com.brainery.serve",
        "systemd_unit": "brainery-serve",
        "description": "Brainery Clip Server",
        "args": ["serve"],
        "log": "serve.log",
    },
    "watch": {
        "label": "com.brainery.watch",
        "systemd_unit": "brainery-watch",
        "description": "Brainery Watch Daemon",
        "args": ["watch", "--foreground"],
        "log": "watch-service.log",
    },
}


def install_service(name: str = "serve") -> bool:
    """Install and start an auto-start service. Returns True on success."""
    if name not in SERVICES:
        print(f"[error] Unknown service: {name}")
        return False

    brainery_bin = _find_brainery_bin()
    if not brainery_bin:
        print("[error] Cannot find 'brainery' binary. Is it installed?")
        return False

    svc = SERVICES[name]

    if platform.system() == "Darwin":
        return _install_launchd(brainery_bin, svc)
    elif platform.system() == "Linux":
        return _install_systemd(brainery_bin, svc)
    else:
        print(f"[warn] Auto-start not supported on {platform.system()}.")
        return False


def uninstall_service(name: str = "serve") -> bool:
    """Stop and remove an auto-start service."""
    if name not in SERVICES:
        print(f"[error] Unknown service: {name}")
        return False

    svc = SERVICES[name]

    if platform.system() == "Darwin":
        return _uninstall_launchd(svc)
    elif platform.system() == "Linux":
        return _uninstall_systemd(svc)
    return False


def is_running(name: str = "serve") -> bool:
    """Check if a service is currently running."""
    if name == "serve":
        import urllib.request
        try:
            with urllib.request.urlopen("http://127.0.0.1:52337/api/ping", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    if name == "watch":
        # Check via PID file (legacy) or service status
        pid_file = Path.home() / ".brainery" / "watch.pid"
        if pid_file.exists():
            try:
                import os
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                return True
            except (ValueError, OSError):
                pass

        # Check via launchd/systemd
        svc = SERVICES[name]
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["launchctl", "list", svc["label"]],
                capture_output=True,
            )
            return result.returncode == 0
        elif platform.system() == "Linux":
            result = subprocess.run(
                ["systemctl", "--user", "is-active", svc["systemd_unit"]],
                capture_output=True,
            )
            return result.returncode == 0

    return False


# ── macOS (launchd) ──────────────────────────────────────────────────────────

def _launchd_plist_path(svc: dict) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{svc['label']}.plist"


def _install_launchd(brainery_bin: str, svc: dict) -> bool:
    plist_path = _launchd_plist_path(svc)
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    log_path = Path.home() / ".brainery" / svc["log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)

    program_args = "\n".join(
        f"        <string>{arg}</string>"
        for arg in [brainery_bin, *svc["args"]]
    )

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{svc['label']}</string>
    <key>ProgramArguments</key>
    <array>
{program_args}
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


def _uninstall_launchd(svc: dict) -> bool:
    plist_path = _launchd_plist_path(svc)
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink()
        print(f"  Service removed: {plist_path}")
        return True
    print(f"  No launchd service found for {svc['label']}.")
    return False


# ── Linux (systemd) ──────────────────────────────────────────────────────────

def _systemd_unit_path(svc: dict) -> Path:
    return Path.home() / ".config" / "systemd" / "user" / f"{svc['systemd_unit']}.service"


def _install_systemd(brainery_bin: str, svc: dict) -> bool:
    unit_path = _systemd_unit_path(svc)
    unit_path.parent.mkdir(parents=True, exist_ok=True)

    exec_start = " ".join([brainery_bin, *svc["args"]])

    unit_content = f"""[Unit]
Description={svc['description']}
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""

    unit_path.write_text(unit_content)

    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", svc["systemd_unit"]], capture_output=True)
    result = subprocess.run(
        ["systemctl", "--user", "start", svc["systemd_unit"]],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print(f"[error] systemctl start failed: {result.stderr.strip()}")
        return False

    print(f"  Service installed: {unit_path}")
    return True


def _uninstall_systemd(svc: dict) -> bool:
    unit_path = _systemd_unit_path(svc)
    if unit_path.exists():
        subprocess.run(["systemctl", "--user", "stop", svc["systemd_unit"]], capture_output=True)
        subprocess.run(["systemctl", "--user", "disable", svc["systemd_unit"]], capture_output=True)
        unit_path.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        print(f"  Service removed: {unit_path}")
        return True
    print(f"  No systemd service found for {svc['systemd_unit']}.")
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
