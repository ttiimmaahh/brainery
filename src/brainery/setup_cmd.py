"""Interactive setup wizard for Brainery configuration."""

from pathlib import Path

from brainery.config import save_config


def run(args, cfg):
    """Run interactive setup wizard."""
    print("Welcome to Brainery Setup!")
    print()

    # KB Paths
    print("=== KB Paths ===")
    personal_kb_path = _prompt(
        "Personal KB path (default ~/.brainery/personal)",
        cfg.get("personal_kb_path", str(Path.home() / ".brainery" / "personal")),
    )
    cfg["personal_kb_path"] = personal_kb_path

    work_kb_path = _prompt(
        "Work KB path (optional, leave blank to skip)",
        cfg.get("work_kb_path", ""),
    )
    if work_kb_path:
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
        cfg.get("llm_backend", "anthropic"),
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
            cfg.get("default_model", "claude-opus-4-5"),
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
    print("\nSetup complete!")


def _setup_local_llm(cfg: dict) -> None:
    """Configure local LLM backend."""
    model_path = _prompt(
        "Path to local model (GGUF or similar)",
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
        "Threads (0 for auto-detect)",
        str(cfg.get("local_model_threads", 0)),
    )
    try:
        cfg["local_model_threads"] = int(threads)
    except ValueError:
        cfg["local_model_threads"] = 0

    gpu_layers = _prompt(
        "GPU layers (0 to disable)",
        str(cfg.get("local_model_gpu_layers", 0)),
    )
    try:
        cfg["local_model_gpu_layers"] = int(gpu_layers)
    except ValueError:
        cfg["local_model_gpu_layers"] = 0

    print()


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
