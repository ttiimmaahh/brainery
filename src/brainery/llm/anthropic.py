"""Anthropic Claude API backend."""

from __future__ import annotations

import os
import subprocess
import sys


def call(cfg: dict, prompt: str, max_tokens: int) -> str:
    try:
        import anthropic
    except ImportError:
        import shutil
        print("  [info] Installing anthropic SDK...")
        if shutil.which("uv"):
            subprocess.run(
                ["uv", "pip", "install", "--python", sys.executable, "anthropic"],
                check=True,
            )
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "anthropic", "-q"],
                check=True,
            )
        import anthropic

    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[error] No Anthropic API key found.")
        print("  Set ANTHROPIC_API_KEY env var or run: kb setup")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    model = cfg.get("default_model", "claude-opus-4-5")

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
