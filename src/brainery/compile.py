"""Compile raw files into structured wiki articles using the LLM."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from brainery.config import get_kb_path, load_prompt
from brainery.llm import call_llm


def run(args, cfg):
    """Compile raw files into structured wiki articles."""
    kb = args.kb or cfg.get("default_kb", "personal")
    recompile_all = getattr(args, "all", False)

    kb_path = get_kb_path(cfg, kb)
    raw_dir = kb_path / "raw"
    wiki_dir = kb_path / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # Find raw files
    raw_files = sorted(
        [f for f in raw_dir.glob("*") if f.is_file() and not f.name.endswith(".meta.json")]
    )

    if not raw_files:
        print("No raw files to compile.")
        return

    # Find compiled sources
    compiled_sources = get_compiled_sources(wiki_dir)

    # Filter uncompiled
    if recompile_all:
        to_compile = raw_files
    else:
        to_compile = [f for f in raw_files if f.name not in compiled_sources]

    if not to_compile:
        print("No uncompiled files.")
        return

    print(f"Compiling {len(to_compile)} file(s)...")

    compile_prompt_template = load_prompt(cfg, "compile")

    for raw_file in to_compile:
        print(f"  {raw_file.name}...", end=" ")
        sys.stdout.flush()

        # Load metadata
        meta_file = raw_dir / f"{raw_file.name}.meta.json"
        domain = None
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            domain = meta.get("domain_override")

        # Read raw content (capped)
        raw_content = raw_file.read_text(encoding="utf-8")
        if len(raw_content) > 12000:
            raw_content = raw_content[:12000] + "\n[... truncated ...]"

        # Derive domain from content or default
        if not domain:
            domain = "general"

        # Build summary of existing articles
        existing_summary = get_existing_articles_summary(wiki_dir, domain)

        # Build index summary
        index_path = wiki_dir / "_index.md"
        index_summary = ""
        if index_path.exists():
            index_content = index_path.read_text()
            # Extract first 500 chars of index
            index_summary = index_content[:500]

        # Fill prompt template
        kb_type = cfg.get("kb_type", "personal knowledge base")
        prompt = compile_prompt_template.format(
            kb_type=kb_type,
            raw_file=raw_file.name,
            domain=domain,
            existing_articles=existing_summary,
            index_summary=index_summary,
            raw_content=raw_content,
        )

        # Call LLM
        try:
            result_text = call_llm(cfg, prompt, max_tokens=4096)
        except Exception as e:
            print(f"[error: {e}]")
            continue

        # Parse and save
        try:
            save_compiled_article(result_text, wiki_dir, index_path, raw_file.name)
            print("ok")
        except Exception as e:
            print(f"[parse error: {e}]")


def get_compiled_sources(wiki_dir: Path) -> set[str]:
    """Scan wiki articles for source_file: frontmatter to find compiled sources."""
    sources = set()
    if not wiki_dir.exists():
        return sources

    for article in wiki_dir.rglob("*.md"):
        if article.name.startswith("_"):
            continue
        content = article.read_text(encoding="utf-8")
        # Look for source_file: pattern in frontmatter
        match = re.search(r"source_file:\s*(.+?)(?:\n|$)", content)
        if match:
            sources.add(match.group(1).strip())

    return sources


def get_existing_articles_summary(wiki_dir: Path, domain: str) -> str:
    """Build a one-line summary of existing articles in a domain."""
    domain_dir = wiki_dir / "domains" / domain
    if not domain_dir.exists():
        return "(no existing articles)"

    articles = list(domain_dir.glob("*.md"))
    if not articles:
        return "(no existing articles)"

    summary_lines = []
    for article in sorted(articles)[:20]:  # Max 20
        content = article.read_text(encoding="utf-8")
        # Extract title from frontmatter
        title_match = re.search(r"title:\s*(.+?)(?:\n|$)", content)
        title = title_match.group(1).strip() if title_match else article.stem
        summary_lines.append(f"- {title}")

    return "\n".join(summary_lines) if summary_lines else "(no existing articles)"


def save_compiled_article(result_text: str, wiki_dir: Path, index_path: Path, source_filename: str) -> None:
    """Parse LLM result and save article + index entry.

    Expects result_text to contain:
    DOMAIN: <domain>
    --- ARTICLE ---
    <markdown with frontmatter>
    --- INDEX_ENTRY ---
    <index entry>
    """
    # Parse sections
    domain_match = re.search(r"DOMAIN:\s*(.+?)(?:\n|$)", result_text)
    domain = domain_match.group(1).strip() if domain_match else "general"

    article_match = re.search(r"--- ARTICLE ---(.+?)(?:--- INDEX_ENTRY ---|$)", result_text, re.DOTALL)
    article_text = article_match.group(1).strip() if article_match else result_text

    index_match = re.search(r"--- INDEX_ENTRY ---(.+?)$", result_text, re.DOTALL)
    index_entry = index_match.group(1).strip() if index_match else ""

    # Extract title from frontmatter
    title_match = re.search(r"title:\s*(.+?)(?:\n|$)", article_text)
    title = title_match.group(1).strip() if title_match else "Untitled"

    # Slugify title
    slug = quote(title.lower().replace(" ", "-"), safe="")[:80]
    if not slug:
        slug = "article"

    # Create domain directory
    domain_dir = wiki_dir / "domains" / domain
    domain_dir.mkdir(parents=True, exist_ok=True)

    # Save article
    article_path = domain_dir / f"{slug}.md"
    # Add source_file to frontmatter
    if "---" in article_text:
        parts = article_text.split("---", 2)
        frontmatter = parts[1]
        if "source_file:" not in frontmatter:
            frontmatter = frontmatter.rstrip() + f"\nsource_file: {source_filename}\n"
        article_text = f"---{frontmatter}---{parts[2]}"
    else:
        article_text = f"---\nsource_file: {source_filename}\n---\n{article_text}"

    article_path.write_text(article_text, encoding="utf-8")

    # Update index
    if not index_path.exists():
        index_path.write_text(
            f"# Wiki Index\n\nLast compiled: {datetime.utcnow().isoformat()}Z\n\n## Article Index\n\n",
            encoding="utf-8",
        )

    index_content = index_path.read_text(encoding="utf-8")
    # Update timestamp
    index_content = re.sub(
        r"Last compiled: .+",
        f"Last compiled: {datetime.utcnow().isoformat()}Z",
        index_content,
    )
    # Append index entry if not already there
    if index_entry and index_entry not in index_content:
        index_content += f"\n{index_entry}\n"

    index_path.write_text(index_content, encoding="utf-8")
