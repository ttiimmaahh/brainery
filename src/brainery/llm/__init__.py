"""LLM backend abstraction for Brainery.

call_llm(cfg, prompt, max_tokens) is the single public entry point.
It routes to the configured backend (anthropic | local).
"""

from brainery.llm.router import call_llm

__all__ = ["call_llm"]
