"""Interactive setup wizard for Brainery configuration."""

from __future__ import annotations

import shutil
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

    # LLM Backend — auto-detect and present options
    print("=== LLM Backend ===")
    _setup_llm_backend(cfg)

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


def _setup_llm_backend(cfg: dict) -> None:
    """Detect available LLM backends and let the user choose."""
    print("  Scanning for available LLM backends...")
    detected = detect_backends()

    options = []
    for backend in detected:
        options.append(backend)
        tag = backend["tag"]
        label = backend["label"]
        detail = backend["detail"]
        print(f"    {len(options)}) {label}")
        if detail:
            print(f"       {detail}")

    # Always offer Anthropic API as an option
    if not any(b["tag"] == "anthropic" for b in options):
        options.append({
            "tag": "anthropic",
            "label": "Anthropic API (requires API key)",
            "detail": "",
        })
        print(f"    {len(options)}) Anthropic API (requires API key)")

    print()

    if not options:
        print("  No backends detected. Configure manually later with: kb setup")
        return

    # Find default selection
    current = cfg.get("llm_backend", "")
    default_idx = "1"
    for i, opt in enumerate(options, 1):
        if opt["tag"] == current:
            default_idx = str(i)
            break

    choice = _prompt("Choose a backend", default_idx)
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        selected = options[int(choice) - 1]
    else:
        # Try matching by tag name
        selected = next((o for o in options if o["tag"] == choice), options[0])

    tag = selected["tag"]
    cfg["llm_backend"] = tag
    print()

    if tag == "ollama":
        _configure_ollama(cfg, selected)
    elif tag == "lmstudio":
        _configure_lmstudio(cfg, selected)
    elif tag == "local":
        _configure_local_llm(cfg)
    elif tag == "anthropic":
        _configure_anthropic(cfg)

    print()


def detect_backends() -> list[dict]:
    """Detect available LLM backends on this system. Returns list of dicts with tag, label, detail."""
    backends = []

    # 1. Check Ollama
    ollama_models = _detect_ollama()
    if ollama_models is not None:
        count = len(ollama_models)
        detail = f"{count} model(s) available" if count else "running but no models pulled"
        backends.append({
            "tag": "ollama",
            "label": f"Ollama ({detail})",
            "detail": ", ".join(ollama_models[:5]) + ("..." if count > 5 else "") if ollama_models else "",
            "models": ollama_models,
        })

    # 2. Check LM Studio
    lmstudio_models = _detect_lmstudio()
    if lmstudio_models is not None:
        count = len(lmstudio_models)
        detail = f"{count} model(s) loaded" if count else "server running"
        backends.append({
            "tag": "lmstudio",
            "label": f"LM Studio ({detail})",
            "detail": ", ".join(lmstudio_models[:5]) if lmstudio_models else "",
            "models": lmstudio_models,
        })

    # 3. Check for local GGUF files (llama-cpp-python)
    gguf_files = _find_local_models()
    if gguf_files:
        backends.append({
            "tag": "local",
            "label": f"llama-cpp-python ({len(gguf_files)} .gguf file(s) found)",
            "detail": Path(gguf_files[0]).name if gguf_files else "",
            "models": gguf_files,
        })

    # 4. Anthropic (always available if they have a key)
    backends.append({
        "tag": "anthropic",
        "label": "Anthropic API (cloud)",
        "detail": "",
    })

    return backends


def _detect_ollama() -> list[str] | None:
    """Check if Ollama is available. Returns model list, or None if not found."""
    # First check if the binary exists
    if not shutil.which("ollama"):
        return None

    # Try the API (server might not be running)
    from brainery.llm.ollama import list_models
    models = list_models()
    return models if models is not None else []


def _detect_lmstudio() -> list[str] | None:
    """Check if LM Studio server is running. Returns model list, or None if not reachable."""
    from brainery.llm.lmstudio import list_models
    models = list_models()
    return models if models else None


def _configure_ollama(cfg: dict, detected: dict) -> None:
    """Configure Ollama backend."""
    host = _prompt("Ollama host", cfg.get("ollama_host", "http://localhost:11434"))
    cfg["ollama_host"] = host

    models = detected.get("models", [])
    if models:
        print("  Available models:")
        for i, m in enumerate(models, 1):
            print(f"    {i}) {m}")
        print()
        choice = _prompt(
            "Choose a model (number or name)",
            cfg.get("ollama_model") or ("1" if models else ""),
        )
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            cfg["ollama_model"] = models[int(choice) - 1]
        else:
            cfg["ollama_model"] = choice
    else:
        model = _prompt("Model name (e.g. 'llama3', 'gemma2')", cfg.get("ollama_model", ""))
        cfg["ollama_model"] = model
        if not model:
            print("  Tip: pull a model with: ollama pull llama3")


def _configure_lmstudio(cfg: dict, detected: dict) -> None:
    """Configure LM Studio backend."""
    host = _prompt("LM Studio host", cfg.get("lmstudio_host", "http://localhost:1234"))
    cfg["lmstudio_host"] = host

    models = detected.get("models", [])
    if models:
        print("  Available models:")
        for i, m in enumerate(models, 1):
            print(f"    {i}) {m}")
        print()
        choice = _prompt(
            "Choose a model (number or name)",
            cfg.get("lmstudio_model") or ("1" if models else ""),
        )
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            cfg["lmstudio_model"] = models[int(choice) - 1]
        else:
            cfg["lmstudio_model"] = choice
    else:
        model = _prompt(
            "Model name (or leave empty for default loaded model)",
            cfg.get("lmstudio_model", ""),
        )
        cfg["lmstudio_model"] = model


def _configure_local_llm(cfg: dict) -> None:
    """Configure llama-cpp-python direct backend."""
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
        print("    - LM Studio  -> File -> Show Models in Finder")
        print("    - Jan.ai     -> ~/jan/models/")
        print("    - llama.cpp  -> wherever you downloaded the .gguf file")
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


def _configure_anthropic(cfg: dict) -> None:
    """Configure Anthropic API backend."""
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


# ── Helpers ──────────────────────────────────────────────────────────────────


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
        print(f"  -> {kb_path}")
    if created_any:
        print()


def _prompt(question: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    prompt_str = f"{question} [{default}]: " if default else f"{question}: "
    try:
        response = input(prompt_str).strip()
    except EOFError:
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
