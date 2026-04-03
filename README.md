# 🧠 Brainery

**A brewery for your brain** — an LLM-powered personal & work knowledge base.

Clip articles, drop in documents, and let Brainery compile them into a structured, searchable wiki. Query it like a research assistant. Run it entirely offline with a local model.

```bash
# One-line install (macOS / Linux)
curl -fsSL https://raw.githubusercontent.com/timpearsoncx/brainery/main/scripts/install.sh | bash
```

---

## How it works

```
Raw content → LLM compilation → Structured wiki → Query / Search / Lint
```

You drop raw material into a `raw/` directory — web clips, PDFs, Word docs, notes.
Brainery's LLM pass reads each file and writes a structured markdown article into `wiki/domains/`,
complete with frontmatter, summaries, backlinks, key concepts, and an auto-maintained index.
No vector database. No complex setup. Just files.

Two silos: **personal** and **work** — same structure, same commands, separate wikis.

---

## Quick start

```bash
# 1. Install
curl -fsSL https://raw.githubusercontent.com/timpearsoncx/brainery/main/scripts/install.sh | bash

# 2. Configure paths and LLM backend
kb setup

# 3. Ingest something
kb ingest https://example.com/interesting-article
kb ingest ~/Downloads/strategy.docx --kb work

# 4. Compile it into your wiki
kb compile

# 5. Ask it anything
kb query "What are the main ideas from my recent AI reading?"
kb query "Summarize our Q1 strategy" --kb work --format slides
```

---

## Commands

| Command | Description |
|---|---|
| `kb setup` | Interactive configuration wizard |
| `kb status` | KB stats: articles, domains, pending compilation |
| `kb ingest <file\|url>` | Add raw content (auto-converts .docx, .pptx, .pdf, URLs) |
| `kb compile` | LLM-compile uncompiled raw files → wiki articles |
| `kb query "<question>"` | Natural language Q&A against your wiki |
| `kb search "<term>"` | Instant full-text search (no LLM) |
| `kb lint` | LLM health check: gaps, broken links, opportunities |
| `kb watch` | Background daemon: auto-compile new files as they arrive |
| `kb install-extension <id>` | Register the KB Clipper Chrome extension |

### Global flags

```
--kb personal|work        Which KB to use (default: from config)
--domain category/sub     Override domain assignment
--format text|md|slides   Output format for kb query
```

---

## LLM backends

Brainery supports two backends, switchable via `kb setup` or `~/.kbconfig.json`:

### Anthropic (cloud)
Best quality for `query` and `lint`. Requires an API key from [console.anthropic.com](https://console.anthropic.com).

```json
{ "llm_backend": "anthropic", "default_model": "claude-opus-4-5" }
```

### Local (llama-cpp-python)
Offline, free, ideal for `kb watch` running continuously in the background.
Any GGUF model works. Recommended: `mistral-7b-instruct`, `llama-3-8b-instruct`, `phi-3-medium`.

```json
{
  "llm_backend": "local",
  "local_model_path": "/path/to/model.gguf",
  "local_model_context": 4096,
  "local_model_gpu_layers": -1
}
```

```bash
pip install "brainery[local]"
kb setup   # select 'local' backend
kb watch   # daemon starts, model loads once, compiles forever
```

---

## Chrome Extension: KB Clipper

Clip web pages directly into your KB with domain tagging — no copy-paste, no file moving.

**Install:**
1. Clone this repo or [download the extension](chrome-extension/)
2. Open `chrome://extensions` → enable Developer mode → Load unpacked → select `chrome-extension/`
3. Copy the extension ID shown
4. Run `kb install-extension <id>`
5. Click the extension icon — the dot turns green ✓

The extension writes clipped pages as markdown directly to your `raw/` directory via a native messaging host. Select personal or work KB, pick a domain, and click **Clip to KB**.

---

## Installation options

### One-line (recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/timpearsoncx/brainery/main/scripts/install.sh | bash
```

### pip
```bash
pip install brainery

# With all optional dependencies
pip install "brainery[full]"
```

### From source
```bash
git clone https://github.com/timpearsoncx/brainery
cd brainery
pip install -e ".[dev]"
```

---

## Agentic coding integration

Drop `skills/SKILL.md` into your project root (or `~/.brainery/SKILL.md`) and your AI coding
assistant — Claude Code, Cursor, Copilot Workspace — will automatically know how to use `kb`
as a tool in its workflows.

```bash
cp skills/SKILL.md ~/your-project/SKILL.md
# or globally:
cp skills/SKILL.md ~/.brainery/SKILL.md
```

The CLI is the interface — no MCP server needed. Any agent that can run shell commands can use Brainery.

---

## Configuration

Config lives at `~/.kbconfig.json`. Edit directly or via `kb setup`.

```json
{
  "personal_kb_path": "/path/to/personal",
  "work_kb_path":     "/path/to/work",
  "default_kb":       "personal",
  "llm_backend":      "anthropic",
  "anthropic_api_key": "sk-ant-...",
  "default_model":    "claude-opus-4-5",
  "local_model_path": "",
  "local_model_context": 4096,
  "local_model_gpu_layers": 0,
  "watch_kbs":        ["personal", "work"]
}
```

---

## Roadmap

- [ ] `kb serve` — local web UI (FastAPI + SPA)
- [ ] `kb tui` — terminal UI (Textual)
- [ ] Firefox extension
- [ ] Windows PowerShell installer
- [ ] `kb sync` — git-based KB backup/sync
- [ ] Homebrew formula

---

## Contributing

Contributions welcome. Please open an issue before submitting large PRs.

```bash
git clone https://github.com/timpearsoncx/brainery
cd brainery
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built with ❤️ and a lot of raw → wiki cycles.*
