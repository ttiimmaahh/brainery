"""Local llama-cpp-python backend for offline / continuous use."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def call(cfg: dict, prompt: str, max_tokens: int) -> str:
    try:
        from llama_cpp import Llama
    except ImportError:
        print("  [info] Installing llama-cpp-python...")
        # Prefer uv (used by uv tool environments), fall back to pip
        import shutil
        if shutil.which("uv"):
            subprocess.run(
                ["uv", "pip", "install", "--python", sys.executable, "llama-cpp-python"],
                check=True,
            )
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "llama-cpp-python", "-q"],
                check=True,
            )
        from llama_cpp import Llama

    model_path = cfg.get("local_model_path", "")
    if not model_path or not Path(model_path).expanduser().exists():
        print(f"[error] Local model not found: '{model_path}'")
        print("  Configure via: kb setup")
        sys.exit(1)

    # Lazy-load and cache the model instance on the cfg dict.
    # The watch daemon calls this repeatedly — loading once saves minutes.
    if "_local_llm_instance" not in cfg:
        model_name = Path(model_path).name
        print(f"  Loading {model_name}...", end="", flush=True)
        threads = cfg.get("local_model_threads") or os.cpu_count() or 4
        cfg["_local_llm_instance"] = Llama(
            model_path=str(Path(model_path).expanduser()),
            n_ctx=cfg.get("local_model_context", 4096),
            n_threads=threads,
            n_gpu_layers=cfg.get("local_model_gpu_layers", 0),
            verbose=False,
        )
        print(" ready.")

    llm = cfg["_local_llm_instance"]

    # Try chat completion first (instruct models), fall back to raw completion.
    try:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise knowledge base compiler. Follow instructions exactly.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
            stop=["</s>", "<|im_end|>", "<|eot_id|>"],
        )
        return response["choices"][0]["message"]["content"]
    except Exception:
        full_prompt = f"### Instruction:\n{prompt}\n\n### Response:\n"
        response = llm(full_prompt, max_tokens=max_tokens, temperature=0.2, echo=False)
        return response["choices"][0]["text"]
