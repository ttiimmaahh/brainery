"""Routes LLM calls to the configured backend."""

from __future__ import annotations


def call_llm(cfg: dict, prompt: str, max_tokens: int = 4096) -> str:
    """Single entry point for all LLM calls. Routes based on cfg['llm_backend']."""
    backend = cfg.get("llm_backend", "anthropic")
    if backend == "local":
        from brainery.llm.local import call as call_local
        return call_local(cfg, prompt, max_tokens)
    from brainery.llm.anthropic import call as call_anthropic
    return call_anthropic(cfg, prompt, max_tokens)
