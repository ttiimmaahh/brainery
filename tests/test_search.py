"""Tests for brainery.search module."""

import textwrap
from pathlib import Path
from unittest import mock


def _make_wiki(tmp_path: Path) -> Path:
    """Create a minimal wiki structure for testing."""
    wiki = tmp_path / "wiki"
    domain = wiki / "domains" / "technology" / "ai-ml"
    domain.mkdir(parents=True)
    (domain / "transformers.md").write_text(textwrap.dedent("""\
        ---
        title: "Transformers"
        domain: technology/ai-ml
        ---

        Transformers are a neural network architecture based on self-attention.
        The attention mechanism allows the model to weigh token relationships.
    """))
    (domain / "llms.md").write_text(textwrap.dedent("""\
        ---
        title: "Large Language Models"
        domain: technology/ai-ml
        ---

        Large language models are trained on vast amounts of text data.
        They use transformer architecture and attention mechanisms.
    """))
    return wiki


def test_search_finds_matching_files(tmp_path, capsys):
    """search returns files containing the search term."""
    wiki = _make_wiki(tmp_path)
    kb_path = tmp_path
    cfg = {"personal_kb_path": str(kb_path), "_kb_override": None}
    args = mock.SimpleNamespace(term="attention", kb=None, domain=None)

    with mock.patch("brainery.config.get_kb_path", return_value=kb_path):
        from brainery.search import run
        run(args, cfg)

    captured = capsys.readouterr()
    assert "attention" in captured.out.lower() or "transformers" in captured.out.lower()


def test_search_no_results(tmp_path, capsys):
    """search prints no-results message when term not found."""
    wiki = _make_wiki(tmp_path)
    kb_path = tmp_path
    args = mock.SimpleNamespace(term="zzznomatch", kb=None, domain=None)

    with mock.patch("brainery.config.get_kb_path", return_value=kb_path):
        from brainery.search import run
        run(args, cfg={"personal_kb_path": str(kb_path), "_kb_override": None})

    captured = capsys.readouterr()
    assert "no results" in captured.out.lower() or "zzznomatch" in captured.out.lower()
