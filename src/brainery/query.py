"""Query the wiki using the LLM with keyword-scored article retrieval."""

import sys
from datetime import datetime
from pathlib import Path

from brainery.config import get_kb_path, load_prompt
from brainery.llm import call_llm


def run(args, cfg):
    """Query the wiki using LLM."""
    question = args.question
    kb = args.kb or cfg.get("default_kb", "personal")
    domain_scope = getattr(args, "domain", "all")
    output_format = getattr(args, "format", "text")

    kb_path = get_kb_path(cfg, kb)
    wiki_dir = kb_path / "wiki"

    # Gather relevant articles
    articles = gather_relevant_articles(wiki_dir, question, domain_scope, max_articles=15)

    if not articles:
        print("No relevant articles found.")
        return

    # Build article context
    articles_context = "\n---\n".join([f"# {path}\n\n{content[:2000]}" for path, content in articles])

    # Load query prompt
    query_prompt_template = load_prompt(cfg, "query")
    prompt = query_prompt_template.format(
        question=question,
        articles_context=articles_context,
        domain_scope=domain_scope,
    )

    # Call LLM
    try:
        result = call_llm(cfg, prompt, max_tokens=4096)
    except Exception as e:
        print(f"[error] Query failed: {e}")
        sys.exit(1)

    # Output
    if output_format == "markdown":
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slug = question.lower().replace(" ", "_")[:40]
        output_dir = kb_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{timestamp}_{slug}.md"
        output_file.write_text(result, encoding="utf-8")
        print(f"Saved to: {output_file}")
    elif output_format == "slides":
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slug = question.lower().replace(" ", "_")[:40]
        output_dir = kb_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{timestamp}_{slug}_slides.md"
        output_file.write_text(result, encoding="utf-8")
        print(f"Saved to: {output_file}")
    else:
        print(result)


def gather_relevant_articles(
    wiki_dir: Path,
    question: str,
    domain_scope: str = "all",
    max_articles: int = 15,
) -> list[tuple[str, str]]:
    """Gather relevant articles by keyword scoring.

    Returns list of (relative_path, content) tuples sorted by relevance.
    """
    # Build list of keywords from question (strip common stop words)
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "is", "was", "are", "be", "been", "being", "have", "has", "do",
        "does", "did", "will", "would", "should", "could", "can", "what", "how",
        "why", "where", "when", "this", "that", "these", "those", "it", "its",
        "as", "by", "with", "from", "up", "about", "out", "if", "so", "than",
    }
    keywords = [
        word.lower()
        for word in question.split()
        if word.lower() not in stop_words and len(word) > 2
    ]

    # Walk wiki and score articles
    articles_with_scores = []

    def walk_dir(d: Path, domain_prefix: str = ""):
        if not d.exists():
            return
        for item in d.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                walk_dir(item, domain_prefix + item.name + "/")
            elif item.is_file() and item.suffix == ".md" and not item.name.startswith("_"):
                # Check domain filter
                if domain_scope != "all" and not domain_prefix.startswith(domain_scope + "/"):
                    continue

                content = item.read_text(encoding="utf-8")
                score = sum(content.lower().count(kw) for kw in keywords)

                if score > 0:
                    rel_path = str(item.relative_to(wiki_dir))
                    articles_with_scores.append((rel_path, content, score))

    walk_dir(wiki_dir)

    # Sort by score (descending)
    articles_with_scores.sort(key=lambda x: x[2], reverse=True)

    # Return top N
    return [(path, content) for path, content, _ in articles_with_scores[:max_articles]]
