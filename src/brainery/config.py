"""Config loading, saving, and path resolution for Brainery."""

import json
import shutil
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".kbconfig.json"
DEFAULT_PROMPTS_DIR = Path.home() / ".brainery" / "prompts"

DEFAULT_CONFIG: dict = {
    "personal_kb_path": "",
    "work_kb_path": "",
    "anthropic_api_key": "",
    "default_kb": "personal",
    "default_model": "claude-opus-4-5",
    "llm_backend": "anthropic",
    "local_model_path": "",
    "local_model_context": 4096,
    "local_model_threads": 0,       # 0 = auto-detect cpu count
    "local_model_gpu_layers": 0,
    "watch_kbs": ["personal", "work"],
    "prompts_path": str(DEFAULT_PROMPTS_DIR),
}


def load_config() -> dict:
    """Load config from disk, merging with defaults for any missing keys."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            on_disk = json.load(f)
        return {**DEFAULT_CONFIG, **on_disk}
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    """Persist config to disk (strips internal runtime keys like _local_llm_instance)."""
    safe = {k: v for k, v in cfg.items() if not k.startswith("_")}
    with open(CONFIG_PATH, "w") as f:
        json.dump(safe, f, indent=2)
    print(f"  Config saved → {CONFIG_PATH}")


def get_kb_path(cfg: dict, kb: str) -> Path:
    key = f"{kb}_kb_path"
    p = cfg.get(key, "")
    if not p:
        print(f"[error] No path configured for '{kb}' KB. Run: kb setup")
        sys.exit(1)
    return Path(p).expanduser()


def get_prompts_path(cfg: dict) -> Path:
    """Return the active prompts directory, initializing defaults if needed."""
    prompts_dir = Path(cfg.get("prompts_path", str(DEFAULT_PROMPTS_DIR))).expanduser()
    if not prompts_dir.exists():
        _bootstrap_prompts(prompts_dir)
    return prompts_dir


def load_prompt(cfg: dict, prompt_name: str) -> str:
    """Load a prompt template by name (e.g. 'compile', 'query', 'lint')."""
    prompts_dir = get_prompts_path(cfg)
    prompt_path = prompts_dir / f"{prompt_name}.md"
    if not prompt_path.exists():
        print(f"[error] Prompt not found: {prompt_path}")
        sys.exit(1)
    return prompt_path.read_text()


def load_domains(cfg: dict) -> dict:
    prompts_dir = get_prompts_path(cfg)
    domains_path = prompts_dir / "domains.json"
    if domains_path.exists():
        return json.loads(domains_path.read_text())
    return {}


def _bootstrap_prompts(dest: Path) -> None:
    """Copy bundled default prompts to the user's prompts dir on first run."""
    src = Path(__file__).parent / "prompts"
    if src.exists():
        shutil.copytree(src, dest)
    else:
        dest.mkdir(parents=True, exist_ok=True)
