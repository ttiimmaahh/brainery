"""Register the KB Clipper Chrome extension native messaging host."""

import json
import sys
from pathlib import Path


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
        sys.exit(1)

    # Determine platform and install paths
    installed_browsers = _install_native_manifest(extension_id, native_host_path)

    if not installed_browsers:
        print("[error] Failed to install native manifest.")
        sys.exit(1)

    print(f"Configured for: {', '.join(installed_browsers)}")
    print(f"\nNext steps:")
    print(f"1. Install the KB Clipper Chrome extension (ID: {extension_id})")
    print(f"2. Grant 'nativeMessaging' permission when prompted")
    print(f"3. Start using the clipper!")


def _is_valid_extension_id(ext_id: str) -> bool:
    """Check if extension ID looks valid (32 hex chars)."""
    if len(ext_id) == 32:
        try:
            int(ext_id, 16)
            return True
        except ValueError:
            pass
    return False


def _find_native_host_script() -> Path:
    """Locate kb_clipper.py relative to package."""
    # Try relative to this module
    module_dir = Path(__file__).parent
    candidates = [
        module_dir.parent.parent.parent / "chrome-extension" / "native" / "kb_clipper.py",
        module_dir / "chrome-extension" / "native" / "kb_clipper.py",
        Path.home() / ".brainery" / "kb_clipper.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _install_native_manifest(extension_id: str, host_script: Path) -> list[str]:
    """Install native messaging manifest to appropriate OS locations."""
    import platform

    os_name = platform.system()
    installed = []

    # Manifest content
    manifest = {
        "name": "com.brainery.kb_clipper",
        "description": "Brainery KB Clipper",
        "path": str(host_script),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }

    if os_name == "Darwin":
        # macOS paths
        browsers = {
            "Chrome": Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts",
            "Brave": Path.home() / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
            "Arc": Path.home() / "Library" / "Application Support" / "Arc" / "NativeMessagingHosts",
        }
    elif os_name == "Linux":
        # Linux paths
        browsers = {
            "Chrome": Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts",
            "Brave": Path.home() / ".config" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
        }
    elif os_name == "Windows":
        # Windows Registry (not handled here; print instructions)
        print("[warning] Windows registry installation not yet automated.")
        print("Manually add registry entry:")
        print(f"  HKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\com.brainery.kb_clipper")
        print(f"  Default: {_write_manifest_file(Path.home() / '.brainery' / 'kb_clipper_manifest.json', manifest)}")
        return ["Chrome (manual)"]
    else:
        return []

    # Install to each browser path
    for browser_name, host_dir in browsers.items():
        try:
            host_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = host_dir / "com.brainery.kb_clipper.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))
            installed.append(browser_name)
        except (PermissionError, OSError) as e:
            pass

    return installed


def _write_manifest_file(path: Path, manifest: dict) -> str:
    """Write manifest to file and return path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2))
    return str(path)
