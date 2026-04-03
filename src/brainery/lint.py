"""Run LLM health checks on the wiki to find issues and opportunities."""

import re
import sys
from datetime import datetime
from pathlib import Path

from brainery.config import get_kb_path, load_prompt
from brainery.llm import call_llm


def run(args, cfg):
    """Run lint checks on the wiki."""
    kb = args.kb or cfg.get("default_kb", "personal")
    domain_scope = getattr(args, "domain", "all")

    kb_path = get_kb_path(cfg, kb)
    wiki_dir = kb_path / "wiki"

    if not wiki_dir.exists():
        print("Wiki directory not found.")
        return

    # Gather article summaries
    summaries = _gather_article_summaries(wiki_dir, domain_scope, max_articles=50)

    if not summaries:
        print("No articles found to lint.")
        return

    summaries_text = "\n".join(summaries)

    # Load lint prompt
    lint_prompt_template = load_prompt(cfg, "lint")
    prompt = lint_prompt_template.format(
        articles=summaries_text,
        domain_scope=domain_scope,
    )

    # Call LLM
    try:
        report = call_llm(cfg, prompt, max_tokens=4096)
    except Exception as e:
        print(f"[error] Lint failed: {e}")
        sys.exit(1)

    # Save report
    output_dir = kb_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"{timestamp}_lint_report.md"
    report_file.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nReport saved to: {report_file}")


def _gather_article_summaries(wiki_dir: Path, domain_scope: str = "all", max_articles: int = 50) -> list[str]:
    """Gather article summaries (title + first 300 chars).

    Returns list of summary strings.
    """
    summaries = []
    articles = []

    # Collect articles
    for markdown_file in sorted(wiki_dir.rglob("*.md")):
        if markdown_file.name.startswith("_"):
            continue

        # Check domain filter
        if domain_scope != "all":
            rel_path = str(markdown_file.relative_to(wiki_dir))
            if not rel_path.startswith(domain_scope):
                continue

        articles.append(markdown_file)

    # Summarize
    for article in articles[:max_articles]:
        try:
            content = article.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        # Extract title
        title_match = re.search(r"title:\s*(.+?)(?:\n|$)", content)
        title = title_match.group(1).strip() if title_match else article.stem

        # Get first 300 chars after frontmatter
        first_para_match = re.search(r"---(.+?)---(.+?)$", content, re.DOTALL)
        body = first_para_match.group(2) if first_para_match else content
        preview = body.strip()[:300]

        summary = f"- **{title}**: {preview}..."
        summaries.append(summary)

    return summaries
