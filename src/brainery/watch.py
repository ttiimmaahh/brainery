"""Background daemon that watches raw/ directories and auto-compiles new files."""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from brainery.config import get_kb_path, load_prompt, load_domains
from brainery.compile import get_compiled_sources, get_existing_articles_summary, save_compiled_article
from brainery.llm import call_llm


WATCH_PID_FILE = Path.home() / ".brainery" / "watch.pid"
WATCH_LOG_FILE = Path.home() / ".brainery" / "watch.log"


def run(args, cfg):
    """Manage watch daemon."""
    # Ensure .brainery directory exists
    WATCH_PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    if getattr(args, "stop", False):
        _stop_daemon()
    elif getattr(args, "status", False):
        _status_daemon()
    else:
        foreground = getattr(args, "foreground", False)
        kb_list = getattr(args, "kb_list", None)
        if kb_list:
            cfg["watch_kbs"] = kb_list.split(",")
        _start_daemon(cfg, foreground)


def _stop_daemon() -> None:
    """Stop the watch daemon."""
    if not WATCH_PID_FILE.exists():
        print("Daemon not running.")
        return

    try:
        pid = int(WATCH_PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        WATCH_PID_FILE.unlink()
        print(f"Stopped daemon (PID {pid}).")
    except (ValueError, ProcessLookupError, FileNotFoundError):
        WATCH_PID_FILE.unlink(missing_ok=True)
        print("Daemon stopped.")


def _status_daemon() -> None:
    """Show daemon status."""
    if not WATCH_PID_FILE.exists():
        print("Daemon not running.")
        return

    try:
        pid = int(WATCH_PID_FILE.read_text().strip())
        print(f"Daemon running (PID {pid}).")

        # Show last few log lines
        if WATCH_LOG_FILE.exists():
            lines = WATCH_LOG_FILE.read_text().strip().split("\n")
            print("\nRecent log:")
            for line in lines[-8:]:
                print(f"  {line}")
    except ValueError:
        print("Daemon status unclear.")


def _start_daemon(cfg: dict, foreground: bool = False) -> None:
    """Start the watch daemon."""
    # Check for existing daemon
    if WATCH_PID_FILE.exists():
        try:
            pid = int(WATCH_PID_FILE.read_text().strip())
            if _is_pid_running(pid):
                print(f"Daemon already running (PID {pid}).")
                return
        except ValueError:
            pass
        WATCH_PID_FILE.unlink(missing_ok=True)

    # Setup logging
    logging.basicConfig(
        filename=str(WATCH_LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
    )
    logger = logging.getLogger()

    if foreground:
        logger.info("Starting watcher (foreground)...")
        _run_watcher(cfg, logger)
    else:
        # Daemonize
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                WATCH_PID_FILE.write_text(str(pid))
                print(f"Started daemon (PID {pid}).")
                return
        except AttributeError:
            # Windows doesn't support fork; fall back to foreground
            print("Fork not available; running in foreground...")
            logger.info("Starting watcher (no fork)...")
            _run_watcher(cfg, logger)
            return

        # Child process
        try:
            os.setsid()
        except (AttributeError, OSError):
            pass

        # Redirect stdout/stderr
        devnull = open(os.devnull, "w")
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        os.dup2(devnull.fileno(), sys.stderr.fileno())

        logger.info("Starting watcher (daemon)...")
        _run_watcher(cfg, logger)
        sys.exit(0)


def _run_watcher(cfg: dict, logger: logging.Logger) -> None:
    """Main watcher loop."""
    # Try to use watchdog if available, else fall back to polling
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        has_watchdog = True
    except ImportError:
        has_watchdog = False
        logger.info("watchdog not available, using polling mode")

    if has_watchdog:
        _run_watcher_event_driven(cfg, logger)
    else:
        _run_watcher_polling(cfg, logger)


def _run_watcher_event_driven(cfg: dict, logger: logging.Logger) -> None:
    """Event-driven watcher using watchdog."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class RawFileHandler(FileSystemEventHandler):
        def __init__(self, cfg_, logger_, debounce_sec=3.0):
            self.cfg = cfg_
            self.logger = logger_
            self.debounce_sec = debounce_sec
            self.last_modified = {}

        def on_created(self, event):
            if event.is_directory or event.src_path.endswith(".meta.json"):
                return
            now = time.time()
            last = self.last_modified.get(event.src_path, 0)
            if now - last > self.debounce_sec:
                self.last_modified[event.src_path] = now
                _auto_compile_file(Path(event.src_path), self.cfg, self.logger)

        def on_modified(self, event):
            # Skip compiled files
            if event.is_directory or event.src_path.endswith(".meta.json"):
                return
            now = time.time()
            last = self.last_modified.get(event.src_path, 0)
            if now - last > self.debounce_sec:
                self.last_modified[event.src_path] = now
                _auto_compile_file(Path(event.src_path), self.cfg, self.logger)

    observer = Observer()
    handler = RawFileHandler(cfg, logger)

    for kb_name in cfg.get("watch_kbs", ["personal"]):
        try:
            kb_path = get_kb_path(cfg, kb_name)
            raw_dir = kb_path / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            observer.schedule(handler, str(raw_dir), recursive=False)
            logger.info(f"Watching: {raw_dir}")
        except Exception as e:
            logger.error(f"Failed to watch {kb_name}: {e}")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def _run_watcher_polling(cfg: dict, logger: logging.Logger) -> None:
    """Polling-based watcher (fallback)."""
    seen_files = {}

    while True:
        try:
            for kb_name in cfg.get("watch_kbs", ["personal"]):
                try:
                    kb_path = get_kb_path(cfg, kb_name)
                    raw_dir = kb_path / "raw"
                    raw_dir.mkdir(parents=True, exist_ok=True)

                    for raw_file in raw_dir.glob("*"):
                        if raw_file.is_file() and not raw_file.name.endswith(".meta.json"):
                            mtime = raw_file.stat().st_mtime
                            if raw_file.name not in seen_files or seen_files[raw_file.name] != mtime:
                                seen_files[raw_file.name] = mtime
                                _auto_compile_file(raw_file, cfg, logger)
                except Exception as e:
                    logger.error(f"Error watching {kb_name}: {e}")

            time.sleep(10)
        except KeyboardInterrupt:
            break


def _auto_compile_file(raw_file: Path, cfg: dict, logger: logging.Logger) -> None:
    """Auto-compile a single raw file."""
    try:
        logger.info(f"Compiling: {raw_file.name}")

        kb_path = raw_file.parent.parent
        wiki_dir = kb_path / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata
        meta_file = raw_file.parent / f"{raw_file.name}.meta.json"
        domain = None
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            domain = meta.get("domain_override")

        # Read raw content (capped)
        raw_content = raw_file.read_text(encoding="utf-8")
        if len(raw_content) > 12000:
            raw_content = raw_content[:12000] + "\n[... truncated ...]"

        # Derive domain
        if not domain:
            domain = "general"

        # Check if already compiled
        compiled_sources = get_compiled_sources(wiki_dir)
        if raw_file.name in compiled_sources:
            logger.info(f"Already compiled: {raw_file.name}")
            return

        # Build context
        existing_summary = get_existing_articles_summary(wiki_dir, domain)
        index_path = wiki_dir / "_index.md"
        index_summary = ""
        if index_path.exists():
            index_summary = index_path.read_text()[:500]

        # Load prompt
        compile_prompt_template = load_prompt(cfg, "compile")
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
        result_text = call_llm(cfg, prompt, max_tokens=4096)

        # Save article
        save_compiled_article(result_text, wiki_dir, index_path, raw_file.name)
        logger.info(f"Compiled: {raw_file.name}")

    except Exception as e:
        logger.error(f"Failed to compile {raw_file.name}: {e}")


def _is_pid_running(pid: int) -> bool:
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
