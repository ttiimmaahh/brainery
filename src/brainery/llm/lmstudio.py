"""LM Studio backend — talks to LM Studio's OpenAI-compatible API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def call(cfg: dict, prompt: str, max_tokens: int) -> str:
    host = cfg.get("lmstudio_host", "http://localhost:1234").rstrip("/")
    model = cfg.get("lmstudio_model", "")

    payload = json.dumps({
        "model": model or "default",
        "messages": [
            {
                "role": "system",
                "content": "You are a precise knowledge base compiler. Follow instructions exactly.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{host}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach LM Studio at {host} — is the server running? ({e})"
        ) from e

    return data["choices"][0]["message"]["content"]


def list_models(host: str = "http://localhost:1234") -> list[str]:
    """Return model names available on the LM Studio server."""
    req = urllib.request.Request(f"{host.rstrip('/')}/v1/models")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return [m["id"] for m in data.get("data", [])]
    except Exception:
        return []
