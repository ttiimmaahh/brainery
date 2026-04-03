"""Register the KB Clipper Chrome extension native messaging host."""

import json
import stat
import sys
from pathlib import Path

NATIVE_HOST_NAME = "com.kb.clipper"


def run(args, cfg):
    """Install native messaging host for Chrome extension."""
    extension_id = args.extension_id

    # Validate extension_id format
    if not _is_valid_extension_id(extension_id):
        print(f"Warning: Extension ID '{extension_id}' doesn't match expected format (32 lowercase hex).")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != "y":
            return

    # Find native host script
    native_host_path = _find_native_host_script()
    if not native_host_path:
        print("[error] Could not find kb_clipper.py native host script.")
        print("  Try reinstalling: pip install --upgrade brainery")
        sys.exit(1)

    # Make it executable
    _ensure_executable(native_host_path)

    # Determine platform and install paths
    installed_browsers = _install_native_manifest(extension_id, native_host_path)

    if not installed_browsers:
        print("[error] Failed to install native manifest.")
        sys.exit(1)

    print(f"\n✓ Native host installed for: {', '.join(installed_browsers)}")
    print(f"  Host name : {NATIVE_HOST_NAME}")
    print(f"  Script    : {native_host_path}")
    print("\nNext steps:")
    print("  1. Reload the KB Clipper extension in Chrome (chrome://extensions → click the reload ↺ icon)")
    print("  2. Click the KB Clipper icon — the dot should turn green ✓")


def _is_valid_extension_id(ext_id: str) -> bool:
    """Check if extension ID looks valid (32 lowercase letters a-p, as Chrome uses base-16 of letters)."""
    return len(ext_id) == 32 and all(c in "abcdefghijklmnop" for c in ext_id.lower())


def _find_native_host_script() -> Path | None:
    """Locate kb_clipper.py — checks bundled package location first, then source tree."""
    module_dir = Path(__file__).parent
    candidates = [
        # Bundled inside the installed package (primary location)
        module_dir / "native" / "kb_clipper.py",
        # Source tree (dev / editable install)
        module_dir.parent.parent.parent / "chrome-extension" / "native" / "kb_clipper.py",
        # Manual override location
        Path.home() / ".brainery" / "kb_clipper.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _ensure_executable(path: Path) -> None:
    """Add executable bit to the script so Chrome can launch it."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_native_manifest(extension_id: str, host_script: Path) -> list[str]:
    """Install native messaging manifest to appropriate OS locations."""
    import platform

    os_name = platform.system()
    installed = []

    # Manifest content — name must match NATIVE_HOST in background.js exactly
    manifest = {
        "name": NATIVE_HOST_NAME,
        "description": "Brainery KB Clipper",
        "path": str(host_script),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }

    manifest_filename = f"{NATIVE_HOST_NAME}.json"

    if os_name == "Darwin":
        browsers = {
            "Chrome": Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts",
            "Brave": Path.home() / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
            "Arc": Path.home() / "Library" / "Application Support" / "Arc" / "NativeMessagingHosts",
            "Chromium": Path.home() / "Library" / "Application Support" / "Chromium" / "NativeMessagingHosts",
        }
    elif os_name == "Linux":
        browsers = {
            "Chrome": Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts",
            "Brave": Path.home() / ".config" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
            "Chromium": Path.home() / ".config" / "chromium" / "NativeMessagingHosts",
        }
    elif os_name == "Windows":
        print("[warning] Windows registry installation not yet automated.")
        print("Manually add a registry entry at:")
        print(f"  HKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\{NATIVE_HOST_NAME}")
        fallback = Path.home() / ".brainery" / manifest_filename
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback.write_text(json.dumps(manifest, indent=2))
        print(f"  Manifest written to: {fallback}")
        return ["Chrome (manual registry step required)"]
    else:
        return []

    for browser_name, host_dir in browsers.items():
        try:
            host_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = host_dir / manifest_filename
            manifest_path.write_text(json.dumps(manifest, indent=2))
            installed.append(browser_name)
        except (PermissionError, OSError):
            pass

    return installed
