"""Ollama backend — talks to a running Ollama server via HTTP."""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error


def call(cfg: dict, prompt: str, max_tokens: int) -> str:
    host = cfg.get("ollama_host", "http://localhost:11434").rstrip("/")
    model = cfg.get("ollama_model", "")
    if not model:
        print("[error] No ollama_model configured. Run: kb setup")
        sys.exit(1)

    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise knowledge base compiler. Follow instructions exactly.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.2,
        },
    }).encode()

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {host} — is it running? ({e})"
        ) from e

    return data["message"]["content"]


def list_models(host: str = "http://localhost:11434") -> list[str]:
    """Return model names available on the Ollama server."""
    req = urllib.request.Request(f"{host.rstrip('/')}/api/tags")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
