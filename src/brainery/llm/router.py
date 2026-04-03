"""Routes LLM calls to the configured backend."""

from __future__ import annotations

BACKENDS = ("anthropic", "ollama", "lmstudio", "local")


def call_llm(cfg: dict, prompt: str, max_tokens: int = 4096) -> str:
    """Single entry point for all LLM calls. Routes based on cfg['llm_backend']."""
    backend = cfg.get("llm_backend", "anthropic")

    if backend == "ollama":
        from brainery.llm.ollama import call as call_ollama
        return call_ollama(cfg, prompt, max_tokens)

    if backend == "lmstudio":
        from brainery.llm.lmstudio import call as call_lmstudio
        return call_lmstudio(cfg, prompt, max_tokens)

    if backend == "local":
        from brainery.llm.local import call as call_local
        return call_local(cfg, prompt, max_tokens)

    # Default: anthropic
    from brainery.llm.anthropic import call as call_anthropic
    return call_anthropic(cfg, prompt, max_tokens)
