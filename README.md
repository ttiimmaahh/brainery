# 🧠 Brainery

> **⚠️ In Development** — This project is actively being built. APIs, commands, and configuration may change. Contributions and feedback welcome!

**A brewery for your brain** — an LLM-powered personal & work knowledge base.

Clip articles, drop in documents, and let Brainery compile them into a structured, searchable wiki. Query it like a research assistant. Run it entirely offline with a local model.

```bash
# One-line install (macOS / Linux)
curl -fsSL https://raw.githubusercontent.com/ttiimmaahh/brainery/main/scripts/install.sh | bash
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
curl -fsSL https://raw.githubusercontent.com/ttiimmaahh/brainery/main/scripts/install.sh | bash

# 2. Configure paths and LLM backend
brainery setup

# 3. Ingest something
brainery ingest https://example.com/interesting-article
brainery ingest ~/Downloads/strategy.docx --kb work

# 4. Compile it into your wiki
brainery compile

# 5. Ask it anything
brainery query "What are the main ideas from my recent AI reading?"
brainery query "Summarize our Q1 strategy" --kb work --format slides
```

> **Tip:** `kb` is a short alias for `brainery` — both commands are installed.
> Power users can type `kb compile`, `kb query`, etc. for speed.

---

## Commands

| Command | Description |
|---|---|
| `brainery setup` | Interactive configuration wizard |
| `brainery status` | KB stats: articles, domains, pending compilation |
| `brainery ingest <file\|url>` | Add raw content (auto-converts .docx, .pptx, .pdf, URLs) |
| `brainery compile` | LLM-compile uncompiled raw files → wiki articles |
| `brainery query "<question>"` | Natural language Q&A against your wiki |
| `brainery search "<term>"` | Instant full-text search (no LLM) |
| `brainery lint` | LLM health check: gaps, broken links, opportunities |
| `brainery watch` | Background daemon: auto-compile new files as they arrive |
| `brainery install-extension <id>` | Register the KB Clipper Chrome extension |

### Global flags

```
--kb personal|work        Which KB to use (default: from config)
--domain category/sub     Override domain assignment
--format text|md|slides   Output format for brainery query
```

---

## LLM backends

Brainery supports four backends, switchable via `brainery setup` or `~/.kbconfig.json`. The setup wizard auto-detects which backends are available on your system.

| Backend | Type | Dependencies | Best for |
|---------|------|-------------|----------|
| **Ollama** | Local server | None (HTTP) | Easy local setup, many model options |
| **LM Studio** | Local server | None (HTTP) | GUI model management, experimentation |
| **llama-cpp-python** | In-process | `llama-cpp-python` | Fully offline, no server needed |
| **Anthropic** | Cloud API | `anthropic` | Best quality, requires API key |

### Ollama
The easiest local option. Install [Ollama](https://ollama.com), pull a model, and go.

```bash
ollama pull llama3
brainery setup   # auto-detects Ollama and lists available models
```

```json
{ "llm_backend": "ollama", "ollama_model": "llama3" }
```

### LM Studio
Use [LM Studio](https://lmstudio.ai) as a backend via its built-in OpenAI-compatible server.

1. Load a model in LM Studio
2. Start the local server (default port 1234)
3. Run `brainery setup` — it detects the running server automatically

```json
{ "llm_backend": "lmstudio", "lmstudio_host": "http://localhost:1234" }
```

### llama-cpp-python (direct)
Loads a GGUF model directly in-process. No server required — fully offline and self-contained. Ideal for `brainery watch` running continuously in the background.

```bash
pip install "brainery[local]"
brainery setup   # scans for .gguf files automatically
```

```json
{
  "llm_backend": "local",
  "local_model_path": "/path/to/model.gguf",
  "local_model_context": 4096,
  "local_model_gpu_layers": -1
}
```

### Anthropic (cloud)
Best quality for `query` and `lint`. Requires an API key from [console.anthropic.com](https://console.anthropic.com).

```json
{ "llm_backend": "anthropic", "default_model": "claude-opus-4-5" }
```

---

## Chrome Extension: KB Clipper

Clip web pages directly into your KB with domain tagging — no copy-paste, no file moving.

**Install:**
1. Clone this repo or [download the extension](chrome-extension/)
2. Open `chrome://extensions` → enable Developer mode → Load unpacked → select `chrome-extension/`
3. Copy the extension ID shown
4. Run `brainery install-extension <id>`
5. Click the extension icon — the dot turns green ✓

The extension writes clipped pages as markdown directly to your `raw/` directory via a native messaging host. Select personal or work KB, pick a domain, and click **Clip to KB**.

---

## Installation options

### One-line (recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/ttiimmaahh/brainery/main/scripts/install.sh | bash
```

### Uninstall
```bash
curl -fsSL https://raw.githubusercontent.com/ttiimmaahh/brainery/main/scripts/uninstall.sh | bash
```

Walks you through removing the CLI, config files, and optionally your KB data (kept by default).

### pip / uv
```bash
pip install brainery

# With all optional dependencies
pip install "brainery[full]"

# Via uv
uv tool install brainery
```

### From source
```bash
git clone https://github.com/ttiimmaahh/brainery
cd brainery
pip install -e ".[dev]"
```

---

## Agentic coding integration

Drop `skills/SKILL.md` into your project root (or `~/.brainery/SKILL.md`) and your AI coding
assistant — Claude Code, Cursor, Copilot Workspace — will automatically know how to use `brainery`
as a tool in its workflows.

```bash
cp skills/SKILL.md ~/your-project/SKILL.md
# or globally:
cp skills/SKILL.md ~/.brainery/SKILL.md
```

The CLI is the interface — no MCP server needed. Any agent that can run shell commands can use Brainery.

---

## Configuration

Config lives at `~/.kbconfig.json`. Edit directly or via `brainery setup`.

```json
{
  "personal_kb_path": "~/.brainery/personal",
  "work_kb_path":     "~/.brainery/work",
  "default_kb":       "personal",
  "llm_backend":      "ollama",
  "anthropic_api_key": "",
  "default_model":    "claude-opus-4-5",
  "ollama_host":      "http://localhost:11434",
  "ollama_model":     "llama3",
  "lmstudio_host":    "http://localhost:1234",
  "lmstudio_model":   "",
  "local_model_path": "",
  "local_model_context": 4096,
  "local_model_gpu_layers": 0,
  "watch_kbs":        ["personal", "work"]
}
```

---

## Roadmap

- [ ] `brainery serve` — local web UI (FastAPI + SPA)
- [ ] `brainery tui` — terminal UI (Textual)
- [ ] Firefox extension
- [ ] Windows PowerShell installer
- [ ] `brainery sync` — git-based KB backup/sync
- [ ] Homebrew formula

---

## Contributing

Contributions welcome. Please open an issue before submitting large PRs.

```bash
git clone https://github.com/ttiimmaahh/brainery
cd brainery
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built with ❤️ and a lot of raw → wiki cycles.*
