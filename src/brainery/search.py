"""Full-text search across the wiki. No LLM needed — instant results."""

import sys
from pathlib import Path

from brainery.config import get_kb_path


def run(args, cfg):
    """Search the wiki for a term."""
    term = args.term
    kb = args.kb or cfg.get("default_kb", "personal")
    domain_scope = getattr(args, "domain", None)

    kb_path = get_kb_path(cfg, kb)
    wiki_dir = kb_path / "wiki"

    if not wiki_dir.exists():
        print("Wiki directory not found.")
        return

    results = _search_wiki(wiki_dir, term, domain_scope)

    if not results:
        print(f"No matches for '{term}'")
        return

    print(f"Found in {len(results)} file(s):\n")

    for filepath, matches in results.items():
        print(f"  {filepath}")
        for line_num, line_text in matches[:3]:  # Show up to 3 matches per file
            # Highlight term
            highlighted = line_text.replace(term, f"[{term}]")
            print(f"    L{line_num}: {highlighted[:100]}")
        if len(matches) > 3:
            print(f"    ... and {len(matches) - 3} more match(es)")
        print()


def _search_wiki(wiki_dir: Path, term: str, domain_scope: str = None) -> dict:
    """Search wiki for term. Returns {filepath: [(line_num, line_text), ...]}.

    Case-insensitive line matching.
    """
    results = {}
    term_lower = term.lower()

    for markdown_file in wiki_dir.rglob("*.md"):
        # Skip index files
        if markdown_file.name.startswith("_"):
            continue

        # Check domain filter
        if domain_scope:
            rel_path = markdown_file.relative_to(wiki_dir)
            if not str(rel_path).startswith(domain_scope):
                continue

        try:
            content = markdown_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        matches = []
        for line_num, line in enumerate(content.split("\n"), 1):
            if term_lower in line.lower():
                matches.append((line_num, line))

        if matches:
            rel_path = str(markdown_file.relative_to(wiki_dir))
            results[rel_path] = matches

    return results
