"""Tests for brainery.config module."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest


def test_load_config_defaults(tmp_path, monkeypatch):
    """load_config returns defaults when no config file exists."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Patch CONFIG_PATH to a non-existent file in tmp_path
    with mock.patch("brainery.config.CONFIG_PATH", tmp_path / ".kbconfig.json"):
        from brainery.config import load_config, DEFAULT_CONFIG
        cfg = load_config()
        assert cfg["default_kb"] == "personal"
        assert cfg["llm_backend"] == "anthropic"
        assert cfg["local_model_context"] == 4096


def test_load_config_merges_with_defaults(tmp_path):
    """load_config merges on-disk values with defaults for missing keys."""
    config_file = tmp_path / ".kbconfig.json"
    config_file.write_text(json.dumps({"personal_kb_path": "/my/kb", "default_kb": "work"}))
    with mock.patch("brainery.config.CONFIG_PATH", config_file):
        from brainery.config import load_config
        cfg = load_config()
        assert cfg["personal_kb_path"] == "/my/kb"
        assert cfg["default_kb"] == "work"
        # Should still have defaults for missing keys
        assert cfg["llm_backend"] == "anthropic"
        assert "local_model_context" in cfg


def test_save_config_strips_runtime_keys(tmp_path):
    """save_config does not persist internal runtime keys (prefixed with _)."""
    config_file = tmp_path / ".kbconfig.json"
    with mock.patch("brainery.config.CONFIG_PATH", config_file):
        from brainery.config import save_config
        cfg = {
            "personal_kb_path": "/my/kb",
            "_local_llm_instance": object(),  # runtime only
            "_kb_override": "work",
        }
        save_config(cfg)
        saved = json.loads(config_file.read_text())
        assert "personal_kb_path" in saved
        assert "_local_llm_instance" not in saved
        assert "_kb_override" not in saved


def test_get_kb_path_exits_when_not_configured(tmp_path):
    """get_kb_path exits with code 1 when path is not configured."""
    with mock.patch("brainery.config.CONFIG_PATH", tmp_path / ".kbconfig.json"):
        from brainery.config import get_kb_path
        cfg = {"personal_kb_path": ""}
        with pytest.raises(SystemExit) as exc:
            get_kb_path(cfg, "personal")
        assert exc.value.code == 1
