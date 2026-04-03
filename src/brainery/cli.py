"""
Brainery CLI — main entry point.

All subcommands delegate to their dedicated module.
This file owns argument parsing only — no business logic lives here.
"""

import argparse
import sys

from brainery import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kb",
        description="Brainery — A brewery for your brain.\nAn LLM-powered personal & work knowledge base.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kb setup                                         Configure paths, API key, LLM backend
  kb status                                        Show KB stats and pending compilation
  kb ingest article.md                             Ingest a local file
  kb ingest https://example.com/post               Ingest a URL
  kb ingest report.docx --kb work --domain projects/active
  kb compile                                       Compile all uncompiled raw files
  kb compile --kb work --all                       Recompile everything in work KB
  kb query "What do I know about transformers?"
  kb query "Q1 strategy summary" --kb work --format markdown
  kb search "retrieval augmented generation"
  kb lint                                          Run wiki health checks
  kb watch                                         Start background auto-compile daemon
  kb watch --stop
  kb install-extension <chrome-extension-id>

LLM backends:
  anthropic   Claude API (cloud) — best quality, requires API key
  local       llama-cpp-python (GGUF) — offline, free, ideal for kb watch daemon

Docs & source: https://github.com/timpearsoncx/brainery
        """,
    )

    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"brainery {__version__}",
    )
    parser.add_argument(
        "--kb",
        choices=["personal", "work"],
        help="Which KB to use (default: from config)",
    )
    parser.add_argument(
        "--domain",
        help="Domain override, e.g. technology/ai-ml",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "slides"],
        help="Output format for kb query",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # ── setup ──────────────────────────────────────────────────────────────────
    sub.add_parser(
        "setup",
        help="Interactive configuration wizard",
    )

    # ── status ─────────────────────────────────────────────────────────────────
    sub.add_parser(
        "status",
        help="Show KB stats and pending compilation queue",
    )

    # ── ingest ─────────────────────────────────────────────────────────────────
    p_ingest = sub.add_parser(
        "ingest",
        help="Add a file or URL to the raw/ directory",
    )
    p_ingest.add_argument("source", help="File path or URL to ingest")

    # ── compile ────────────────────────────────────────────────────────────────
    p_compile = sub.add_parser(
        "compile",
        help="Compile uncompiled raw files into wiki articles",
    )
    p_compile.add_argument(
        "--all",
        action="store_true",
        help="Recompile all files, not just new ones",
    )

    # ── query ──────────────────────────────────────────────────────────────────
    p_query = sub.add_parser(
        "query",
        help="Ask a natural language question against your wiki",
    )
    p_query.add_argument("question", help="The question to ask")

    # ── search ─────────────────────────────────────────────────────────────────
    p_search = sub.add_parser(
        "search",
        help="Full-text search across the wiki (no LLM, instant)",
    )
    p_search.add_argument("term", help="Search term")

    # ── lint ───────────────────────────────────────────────────────────────────
    sub.add_parser(
        "lint",
        help="Run LLM health checks: find gaps, inconsistencies, and opportunities",
    )

    # ── watch ──────────────────────────────────────────────────────────────────
    p_watch = sub.add_parser(
        "watch",
        help="Start background daemon: auto-compile new files as they arrive",
    )
    p_watch.add_argument("--stop", action="store_true", help="Stop the running watcher")
    p_watch.add_argument("--status", action="store_true", help="Show watcher status and log tail")
    p_watch.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Run in foreground (don't daemonize — good for debugging)",
    )
    p_watch.add_argument(
        "--kb-list",
        nargs="+",
        choices=["personal", "work"],
        dest="kb_list",
        help="Which KBs to watch (default: all configured)",
    )

    # ── install-extension ──────────────────────────────────────────────────────
    p_ext = sub.add_parser(
        "install-extension",
        help="Register the Brainery Chrome extension native messaging host",
    )
    p_ext.add_argument(
        "extension_id",
        help="Chrome extension ID (32-char string from chrome://extensions)",
    )

    # ── dispatch ───────────────────────────────────────────────────────────────
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    from brainery.config import load_config

    cfg = load_config()

    # Propagate global flags into cfg for convenience
    if args.kb:
        cfg["_kb_override"] = args.kb
    if args.domain:
        cfg["_domain_override"] = args.domain
    if args.format:
        cfg["_format_override"] = args.format

    _dispatch(args, cfg)


def _dispatch(args, cfg: dict) -> None:
    command = args.command

    if command == "setup":
        from brainery.setup_cmd import run
    elif command == "status":
        from brainery.status import run
    elif command == "ingest":
        from brainery.ingest import run
    elif command == "compile":
        from brainery.compile import run
    elif command == "query":
        from brainery.query import run
    elif command == "search":
        from brainery.search import run
    elif command == "lint":
        from brainery.lint import run
    elif command == "watch":
        from brainery.watch import run
    elif command == "install-extension":
        from brainery.extension import run
    else:
        print(f"[error] Unknown command: {command}")
        sys.exit(1)

    run(args, cfg)


if __name__ == "__main__":
    main()
