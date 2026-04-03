"""Show KB stats: raw files, wiki articles, domains, pending compilation."""

import sys
from collections import defaultdict
from pathlib import Path

from brainery.config import get_kb_path
from brainery.compile import get_compiled_sources


def run(args, cfg):
    """Show KB status and statistics."""
    kb = args.kb or cfg.get("default_kb", "personal")
    kb_path = get_kb_path(cfg, kb)

    raw_dir = kb_path / "raw"
    wiki_dir = kb_path / "wiki"
    output_dir = kb_path / "output"

    # Count raw files
    raw_files = [f for f in raw_dir.glob("*") if f.is_file() and not f.name.endswith(".meta.json")]
    raw_count = len(raw_files)

    # Count uncompiled
    compiled_sources = get_compiled_sources(wiki_dir) if wiki_dir.exists() else set()
    uncompiled = [f for f in raw_files if f.name not in compiled_sources]
    uncompiled_count = len(uncompiled)

    # Count wiki articles
    wiki_articles = list(wiki_dir.rglob("*.md")) if wiki_dir.exists() else []
    wiki_articles = [f for f in wiki_articles if not f.name.startswith("_")]
    article_count = len(wiki_articles)

    # Count output files
    output_files = list(output_dir.glob("*")) if output_dir.exists() else []
    output_count = len(output_files)

    # Domain breakdown
    domain_counts = defaultdict(int)
    for article in wiki_articles:
        rel_path = article.relative_to(wiki_dir)
        domain = str(rel_path.parent)
        if domain != ".":
            # Extract domain from path like "domains/general/..."
            parts = rel_path.parts
            if len(parts) > 1:
                domain = parts[1]
            domain_counts[domain] += 1

    # Print status
    print(f"KB: {kb} ({kb_path})")
    print()
    print(f"Raw files:  {raw_count}")
    if uncompiled_count > 0:
        print(f"Uncompiled: {uncompiled_count}")
    print(f"Articles:   {article_count}")
    print(f"Output:     {output_count}")
    print()

    if domain_counts:
        print("Domains:")
        for domain in sorted(domain_counts.keys()):
            count = domain_counts[domain]
            print(f"  {domain}: {count}")
        print()

    if uncompiled_count > 0:
        print(f"Pending compilation ({uncompiled_count}):")
        for f in uncompiled[:10]:
            print(f"  {f.name}")
        if uncompiled_count > 10:
            print(f"  ... and {uncompiled_count - 10} more")
