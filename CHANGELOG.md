# Changelog

All notable changes to Brainery are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- `kb serve` — local web UI (FastAPI + SPA)
- `kb tui` — terminal UI (Textual)
- Firefox extension support
- Windows PowerShell installer
- `kb sync` — git-based KB backup/sync

---

## [0.1.0] — 2026-04-03

### Added
- Initial release
- `kb ingest` — ingest files (`.md`, `.txt`, `.docx`, `.pptx`, `.pdf`) and URLs
- `kb compile` — LLM-powered compilation of raw files into structured wiki articles
- `kb query` — natural language Q&A against the wiki (text, markdown, slides output)
- `kb search` — instant full-text search (no LLM required)
- `kb lint` — LLM wiki health checks: gaps, broken links, connection opportunities
- `kb watch` — background daemon with watchdog + polling fallback; auto-compiles on new files
- `kb status` — KB stats dashboard
- `kb setup` — interactive configuration wizard
- `kb install-extension` — registers KB Clipper Chrome extension native messaging host
- Dual LLM backend: Anthropic Claude API and local llama-cpp-python (GGUF models)
- Domain taxonomy with auto-detection (`category/subcategory` pattern)
- Chrome extension: KB Clipper — clip web pages directly to `personal/` or `work/` KB
- Native messaging host for Chrome/Brave/Arc (macOS + Linux)
- `skills/SKILL.md` — agentic coding skill file for Claude Code, Cursor, and friends
- macOS + Linux one-line installer (`scripts/install.sh`)
- GitHub Actions CI (Python 3.10–3.12, macOS + Linux) and release pipeline (PyPI + GitHub Releases)

[Unreleased]: https://github.com/timpearsoncx/brainery/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/timpearsoncx/brainery/releases/tag/v0.1.0
