# Brainery KB Skill

> **For agentic coding tools** (Claude Code, Cursor, GitHub Copilot, etc.)
> Drop this file at your project root or `~/.brainery/SKILL.md` and your AI coding assistant
> will automatically know how to query, search, and manage your knowledge base.

---

## What is Brainery?

Brainery is a local, LLM-powered knowledge base CLI. Raw content (articles, docs, PDFs,
web clips) gets compiled into a structured markdown wiki by an LLM. The `kb` command lets
you query, search, and maintain that wiki from any terminal or agentic workflow.

**Two silos**: `personal` (default) and `work`. Each has its own `raw/`, `wiki/`, and `output/`.

---

## Quick Reference

```
kb status                              Show stats and pending compilation
kb ingest <file_or_url>                Add raw content (auto-converts docx, pptx, pdf, URLs)
kb ingest <file> --kb work             Target the work KB
kb ingest <file> --domain tech/ai-ml   Override domain assignment
kb compile                             Compile all uncompiled raw files → wiki articles
kb compile --kb work                   Compile work KB
kb compile --all                       Recompile everything (after prompt changes)
kb query "<question>"                  LLM-powered Q&A against the wiki
kb query "<q>" --format markdown       Save answer as a markdown file to output/
kb query "<q>" --format slides         Save answer as a Marp slide deck
kb query "<q>" --kb work               Query work KB
kb query "<q>" --domain technology     Scope to one domain
kb search "<term>"                     Fast full-text search (no LLM, instant)
kb search "<term>" --kb work
kb lint                                LLM health check: gaps, broken links, opportunities
kb watch                               Background daemon: auto-compile on file changes
kb watch --stop
kb watch --status
kb setup                               Interactive configuration wizard
kb --version
```

---

## How to Use Brainery in Agentic Workflows

### Answering questions about a topic

When a user asks about something that might be in the KB, always try `kb search` first
(fast, no tokens), then `kb query` for synthesis:

```bash
# Step 1: quick search
kb search "transformer attention"

# Step 2: if relevant articles found, query for synthesis
kb query "Explain self-attention mechanisms in transformers"
```

### Before writing code in a domain you've researched

```bash
# Check if the KB has relevant prior art or notes
kb search "authentication"
kb query "What patterns have I noted for JWT auth in Python?" --format text
```

### After completing research or reading

```bash
# Ingest the source first
kb ingest https://example.com/paper-url

# Then compile it into the wiki
kb compile

# Optionally verify it was added
kb status
```

### Adding a document from the work KB

```bash
kb ingest /path/to/strategy.docx --kb work --domain strategy/planning
kb compile --kb work
```

### Getting a synthesis for a meeting or presentation

```bash
kb query "Summarize our Q1 strategy decisions" --kb work --format slides
# Output saved to work/output/{timestamp}-summary.md as Marp slides
```

### Periodic maintenance

```bash
# Weekly: check wiki health
kb lint

# After bulk ingestion: compile everything
kb compile --all
```

---

## Understanding the Output

**`kb search`** returns:
```
  📄 domains/technology/ai-ml/transformers.md
       L12: ...the [attention] mechanism allows...
       L34: ...multi-head [attention] in practice...
```

**`kb query`** returns a synthesized answer with `[[Article Title]]` inline citations.

**`kb status`** returns:
```
  KB: PERSONAL  (/path/to/personal)
  Raw sources:    12 total, 3 uncompiled
  Wiki articles:  47
  Domains:
    technology/ai-ml     14 articles
    finance/investing     8 articles
    ...
```

---

## Domain Taxonomy

Domains follow `category/subcategory` pattern. Common personal domains:
`technology/ai-ml`, `technology/software-engineering`, `finance/investing`,
`health/fitness`, `career/leadership`, `learning/books`

Common work domains:
`projects/active`, `clients/accounts`, `strategy/planning`,
`meetings/decisions`, `research/industry`

The LLM auto-detects domain on compile. Override with `--domain` flag on ingest.

---

## Config Location

`~/.kbconfig.json` — edit directly or via `kb setup`.

Key fields:
```json
{
  "personal_kb_path": "/path/to/KB/personal",
  "work_kb_path":     "/path/to/KB/work",
  "llm_backend":      "anthropic",
  "default_model":    "claude-opus-4-5",
  "local_model_path": "/path/to/model.gguf"
}
```

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/timpearsoncx/brainery/main/scripts/install.sh | bash
```

Source: https://github.com/timpearsoncx/brainery
