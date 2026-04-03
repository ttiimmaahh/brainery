"""Interactive setup wizard for Brainery configuration."""

from pathlib import Path

from brainery.config import save_config

_DEFAULT_PERSONAL = "~/.brainery/personal"
_DEFAULT_WORK = "~/.brainery/work"


def run(args, cfg):
    """Run interactive setup wizard."""
    print("Welcome to Brainery Setup!")
    print()

    # KB Paths
    print("=== KB Paths ===")
    personal_kb_path = _prompt(
        "Personal KB path",
        cfg.get("personal_kb_path") or _DEFAULT_PERSONAL,
    )
    cfg["personal_kb_path"] = personal_kb_path

    work_kb_path = _prompt(
        "Work KB path (press Enter to skip)",
        cfg.get("work_kb_path") or _DEFAULT_WORK,
    )
    cfg["work_kb_path"] = work_kb_path

    default_kb = _prompt(
        "Default KB ('personal' or 'work')",
        cfg.get("default_kb", "personal"),
    )
    cfg["default_kb"] = default_kb
    print()

    # LLM Backend
    print("=== LLM Backend ===")
    llm_backend = _prompt(
        "Backend ('anthropic' or 'local')",
        cfg.get("llm_backend") or "anthropic",
    )
    cfg["llm_backend"] = llm_backend
    print()

    if llm_backend == "anthropic":
        api_key = _prompt_secret(
            "Anthropic API key (or press Enter to keep existing)",
            cfg.get("anthropic_api_key", ""),
        )
        if api_key:
            cfg["anthropic_api_key"] = api_key

        model = _prompt(
            "Model name",
            cfg.get("default_model") or "claude-opus-4-5",
        )
        cfg["default_model"] = model
    else:
        # Local LLM setup
        _setup_local_llm(cfg)

    # Watch settings
    print("=== Watch Settings ===")
    watch_str = _prompt(
        "KBs to watch (comma-separated, e.g. 'personal,work')",
        ",".join(cfg.get("watch_kbs", ["personal"])),
    )
    cfg["watch_kbs"] = [kb.strip() for kb in watch_str.split(",") if kb.strip()]
    print()

    # Save
    save_config(cfg)

    # Create KB directory structures so they're ready to use immediately
    _scaffold_kb_dirs(cfg)

    print("\nSetup complete!")


def _scaffold_kb_dirs(cfg: dict) -> None:
    """Create the raw/, wiki/, and output/ subdirectories for each configured KB."""
    created_any = False
    for key in ["personal_kb_path", "work_kb_path"]:
        path_str = cfg.get(key, "")
        if not path_str:
            continue
        kb_path = Path(path_str).expanduser()
        for subdir in ["raw", "wiki", "output"]:
            target = kb_path / subdir
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
                created_any = True
        print(f"  ✓ {kb_path}")
    if created_any:
        print()


def _setup_local_llm(cfg: dict) -> None:
    """Configure local LLM backend."""
    # Scan for GGUF models in common locations
    detected = _find_local_models()

    if detected:
        print("  Found local models:")
        for i, path in enumerate(detected, 1):
            name = Path(path).name
            print(f"    {i}) {name}")
            print(f"       {path}")
        print()
        choice = _prompt(
            "Enter a number to select, or paste a full path",
            cfg.get("local_model_path", "1"),
        )
        if choice.isdigit() and 1 <= int(choice) <= len(detected):
            model_path = detected[int(choice) - 1]
        else:
            model_path = choice
    else:
        print("  No .gguf models detected automatically.")
        print("  Common sources:")
        print("    • LM Studio  → File → Show Models in Finder")
        print("    • Jan.ai     → ~/jan/models/")
        print("    • llama.cpp  → wherever you downloaded the .gguf file")
        print()
        model_path = _prompt(
            "Path to .gguf model file",
            cfg.get("local_model_path", ""),
        )

    cfg["local_model_path"] = model_path

    context = _prompt(
        "Context window size",
        str(cfg.get("local_model_context", 4096)),
    )
    try:
        cfg["local_model_context"] = int(context)
    except ValueError:
        cfg["local_model_context"] = 4096

    threads = _prompt(
        "Threads (0 = auto-detect)",
        str(cfg.get("local_model_threads", 0)),
    )
    try:
        cfg["local_model_threads"] = int(threads)
    except ValueError:
        cfg["local_model_threads"] = 0

    gpu_layers = _prompt(
        "GPU layers (0 = CPU only, -1 = all layers on GPU)",
        str(cfg.get("local_model_gpu_layers", 0)),
    )
    try:
        cfg["local_model_gpu_layers"] = int(gpu_layers)
    except ValueError:
        cfg["local_model_gpu_layers"] = 0

    print()


def _find_local_models() -> list[str]:
    """Scan common locations for .gguf model files. Returns up to 10 paths."""
    search_dirs = [
        # LM Studio (macOS)
        Path.home() / ".lmstudio" / "models",
        Path.home() / "Library" / "Application Support" / "LM Studio" / "Models",
        # Jan.ai
        Path.home() / "jan" / "models",
        # Generic
        Path.home() / "models",
        Path.home() / ".local" / "share" / "models",
        # LM Studio (Linux)
        Path.home() / ".local" / "share" / "LM Studio" / "Models",
    ]

    found = []
    for d in search_dirs:
        if d.exists():
            for gguf in sorted(d.rglob("*.gguf")):
                found.append(str(gguf))
                if len(found) >= 10:
                    return found
    return found


def _prompt(question: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    prompt_str = f"{question} [{default}]: " if default else f"{question}: "
    try:
        response = input(prompt_str).strip()
    except EOFError:
        # stdin not interactive (e.g. piped); accept the default silently
        print()
        return default
    return response if response else default


def _prompt_secret(question: str, default: str = "") -> str:
    """Prompt for sensitive input (masks input)."""
    import getpass

    prompt_str = f"{question} [***]: " if default else f"{question}: "
    try:
        response = getpass.getpass(prompt_str).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return response if response else default
