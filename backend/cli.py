#!/usr/bin/env python3
"""MiLyfe Brain — Command-Line Interface.

Usage:
    milyfe run "Build a REST API with auth"
    milyfe run --file playbook.json
    milyfe chat "What files are in the workspace?"
    milyfe status
    milyfe health
    milyfe list
    milyfe logs
    milyfe models
    milyfe selftest
    milyfe daemon start|stop|status
    milyfe config get|set <key> [value]

Requires the MiLyfe Brain backend to be running.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    print("Error: httpx required. Install: pip install httpx")
    sys.exit(1)


# ─── Configuration ──────────────────────────────────────────────

DEFAULT_API_URL = "http://localhost:8200"
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}


def c(text: str, color: str) -> str:
    """Colorize text."""
    if not sys.stdout.isatty():
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def get_api_url() -> str:
    """Get API URL from env or default."""
    import os
    return os.environ.get("MILYFE_API_URL", DEFAULT_API_URL)


# ─── API Client ─────────────────────────────────────────────────


async def api_get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{get_api_url()}{path}")
        resp.raise_for_status()
        return resp.json()


async def api_post(path: str, data: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f"{get_api_url()}{path}", json=data or {})
        resp.raise_for_status()
        return resp.json()


# ─── Commands ───────────────────────────────────────────────────


async def cmd_run(args):
    """Run a playbook from text or file."""
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(c(f"Error: File not found: {args.file}", "red"))
            sys.exit(1)
        data = json.loads(path.read_text())
        if "title" not in data:
            data["title"] = path.stem
    else:
        description = " ".join(args.task)
        if not description:
            print(c("Error: Provide a task description or --file", "red"))
            sys.exit(1)
        data = {
            "title": description[:50],
            "description": description,
            "raw_text": description,
            "auto_execute": not args.dry_run,
        }

    if args.dry_run:
        data["auto_execute"] = False

    print(c("Launching playbook...", "cyan"))
    print(f"  Title: {c(data.get('title', 'Untitled'), 'bold')}")
    print()

    try:
        result = await api_post("/api/playbooks/", data)
        playbook_id = result.get("id", "")
        print(c(f"Playbook created: {playbook_id}", "green"))

        if args.dry_run:
            print(c("\n[DRY RUN] Estimating execution...", "yellow"))
            # Call dry-run endpoint
            try:
                dry = await api_post(f"/api/playbooks/{playbook_id}/dry-run")
                print(f"  Steps: {dry.get('total_steps', '?')}")
                print(f"  Estimated time: {dry.get('estimated_time_seconds', '?')}s")
                print(f"  Estimated tokens: {dry.get('estimated_tokens', '?')}")
                print(f"  Cost equivalent: ${dry.get('estimated_cost_equivalent_usd', '?')}")
            except Exception:
                print("  (Dry-run estimation not available)")
            return

        # Poll status
        if not args.no_wait:
            await _poll_status(playbook_id)

    except httpx.HTTPStatusError as e:
        print(c(f"API Error: {e.response.status_code} - {e.response.text[:200]}", "red"))
        sys.exit(1)
    except httpx.ConnectError:
        print(c("Error: Cannot connect to MiLyfe Brain. Is it running?", "red"))
        print(f"  Expected at: {get_api_url()}")
        sys.exit(1)


async def _poll_status(playbook_id: str):
    """Poll playbook status until completion."""
    print(c("\nWatching execution...", "dim"))
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    last_step_count = 0

    while True:
        try:
            status = await api_get(f"/api/playbooks/{playbook_id}/status")
            state = status.get("status", "unknown")
            progress = status.get("progress", 0)
            completed = status.get("completed_steps", 0)
            total = status.get("total_steps", 0)
            running = status.get("running_steps", 0)

            # Progress bar
            bar_width = 30
            filled = int(bar_width * progress)
            bar = "█" * filled + "░" * (bar_width - filled)

            status_line = f"\r  {spinner[idx % len(spinner)]} [{bar}] {progress*100:.0f}% ({completed}/{total} steps)"
            if running:
                status_line += f" | {c(f'{running} running', 'blue')}"

            sys.stdout.write(status_line + "   ")
            sys.stdout.flush()
            idx += 1

            if state == "completed":
                print(f"\n\n{c('✓ Playbook completed successfully!', 'green')}")
                print(f"  Steps: {completed}/{total}")
                break
            elif state == "failed":
                error = status.get("error", "Unknown error")
                print(f"\n\n{c('✗ Playbook failed', 'red')}")
                print(f"  Error: {error}")
                sys.exit(1)

            await asyncio.sleep(1)

        except Exception:
            await asyncio.sleep(2)


async def cmd_chat(args):
    """Send a chat message."""
    message = " ".join(args.message)
    if not message:
        print(c("Error: Provide a message", "red"))
        sys.exit(1)

    print(c(f"You: {message}", "dim"))
    print()

    try:
        result = await api_post("/api/chat/send", {
            "message": message,
            "model_override": args.model,
        })
        content = result.get("content", "No response")
        model = result.get("model", "")

        print(c(f"Brain ({model}):", "cyan"))
        print(content)
        print()

    except httpx.ConnectError:
        print(c("Error: Cannot connect to MiLyfe Brain.", "red"))
        sys.exit(1)


async def cmd_chat_stream(args):
    """Stream a chat response token-by-token."""
    message = " ".join(args.message)
    if not message:
        print(c("Error: Provide a message", "red"))
        sys.exit(1)

    print(c(f"You: {message}", "dim"))
    print()
    print(c("Brain: ", "cyan"), end="", flush=True)

    try:
        url = f"{get_api_url()}/api/stream/chat?message={httpx.URL(message)}"
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "token":
                            print(data.get("content", ""), end="", flush=True)
                        elif data.get("type") == "done":
                            stats = data.get("stats", {})
                            print(f"\n\n{c(f'[{stats.get(\"total_tokens\", 0)} tokens, {stats.get(\"duration_ms\", 0):.0f}ms]', 'dim')}")
                            break
                        elif data.get("type") == "error":
                            print(c(f"\nError: {data.get('content')}", "red"))
                            break
    except Exception as e:
        print(c(f"\nError: {e}", "red"))


async def cmd_status(args):
    """Show system status."""
    try:
        health = await api_get("/health")
        print(c("MiLyfe Brain Status", "bold"))
        print(f"  Status: {c(health.get('status', '?'), 'green' if health.get('status') == 'healthy' else 'red')}")
        print(f"  Version: {health.get('version', '?')}")
        print(f"  Uptime: {health.get('uptime_seconds', 0):.0f}s")
        print()
        print(c("Services:", "bold"))
        for svc, status in health.get("services", {}).items():
            color = "green" if status == "healthy" else "yellow" if status == "unavailable" else "red"
            print(f"  {svc}: {c(status, color)}")

        # Queue status
        print()
        queue = await api_get("/api/queue/status")
        running = queue.get("running")
        waiting = queue.get("waiting", [])
        print(c("Queue:", "bold"))
        print(f"  Running: {running.get('title') if running else 'None'}")
        print(f"  Waiting: {len(waiting)}")

    except httpx.ConnectError:
        print(c("Error: Cannot connect to MiLyfe Brain.", "red"))
        sys.exit(1)


async def cmd_list(args):
    """List playbooks."""
    try:
        playbooks = await api_get("/api/playbooks/")
        if not playbooks:
            print("No playbooks found.")
            return

        print(c(f"{'ID':<12} {'Status':<12} {'Title':<40} {'Created'}", "bold"))
        print("-" * 80)
        for pb in playbooks[:20]:
            status = pb.get("status", "?")
            color = {"completed": "green", "failed": "red", "running": "blue"}.get(status, "dim")
            print(f"{pb['id'][:10]:<12} {c(status:<12, color)} {pb.get('title', '?')[:38]:<40} {pb.get('created_at', '?')[:10]}")

    except httpx.ConnectError:
        print(c("Error: Cannot connect.", "red"))
        sys.exit(1)


async def cmd_health(args):
    """Run self-test."""
    print(c("Running self-test...", "cyan"))
    try:
        result = await api_post("/api/selftest/run")
        print()
        for r in result.get("results", []):
            status = r.get("status", "?")
            color = {"pass": "green", "fail": "red", "skip": "yellow"}.get(status, "dim")
            print(f"  {c(status.upper():<6, color)} {r.get('service', '?'):<20} {r.get('message', ''):<40} {r.get('latency_ms', 0):.0f}ms")
        print()
        passed = result.get("all_passed", False)
        print(c("All tests passed!" if passed else "Some tests failed.", "green" if passed else "red"))
    except httpx.ConnectError:
        print(c("Error: Cannot connect.", "red"))
        sys.exit(1)


async def cmd_models(args):
    """List available Ollama models."""
    try:
        api_url = get_api_url().replace("8200", "11434")  # Ollama port
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"http://localhost:11434/api/tags")
            models = resp.json().get("models", [])

        if not models:
            print("No models found. Pull one: ollama pull phi3:mini")
            return

        print(c(f"{'Model':<30} {'Size':<12} {'Modified'}", "bold"))
        print("-" * 60)
        for m in models:
            name = m.get("name", "?")
            size_gb = m.get("size", 0) / (1024**3)
            modified = m.get("modified_at", "?")[:10]
            print(f"{name:<30} {size_gb:.1f}GB{'':<6} {modified}")

    except Exception as e:
        print(c(f"Error connecting to Ollama: {e}", "red"))


async def cmd_logs(args):
    """Show recent logs."""
    try:
        logs = await api_get(f"/api/logs/?limit={args.limit}")
        for log in logs:
            ts = log.get("timestamp", "")[:19]
            role = log.get("agent_role", "-")
            action = log.get("action_type", "-")
            desc = log.get("description", "")[:60]
            risk = log.get("risk_level", "safe")
            risk_color = {"safe": "green", "caution": "yellow", "dangerous": "red"}.get(risk, "dim")
            print(f"{c(ts, 'dim')} {role:<12} {action:<12} {c(risk, risk_color):<10} {desc}")
    except httpx.ConnectError:
        print(c("Error: Cannot connect.", "red"))
        sys.exit(1)


async def cmd_daemon(args):
    """Control the daemon."""
    action = args.action
    try:
        if action == "status":
            result = await api_get("/api/brain/daemon/status")
            running = result.get("running", False)
            print(f"Daemon: {c('Running', 'green') if running else c('Stopped', 'red')}")
            if result.get("watching_paths"):
                print(f"Watching: {', '.join(result['watching_paths'])}")
            print(f"Events processed: {result.get('events_processed', 0)}")
        elif action == "start":
            await api_post("/api/brain/daemon/start")
            print(c("Daemon started.", "green"))
        elif action == "stop":
            await api_post("/api/brain/daemon/stop")
            print(c("Daemon stopped.", "yellow"))
    except httpx.ConnectError:
        print(c("Error: Cannot connect.", "red"))
        sys.exit(1)


# ─── Argument Parser ────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="milyfe",
        description="MiLyfe Brain CLI — Local AI Agent Swarm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--api-url", help="Backend API URL", default=None)
    sub = parser.add_subparsers(dest="command")

    # run
    p_run = sub.add_parser("run", help="Run a playbook")
    p_run.add_argument("task", nargs="*", help="Task description")
    p_run.add_argument("--file", "-f", help="Playbook JSON file")
    p_run.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    p_run.add_argument("--no-wait", action="store_true", help="Don't wait for completion")
    p_run.add_argument("--model", "-m", help="Model override")

    # chat
    p_chat = sub.add_parser("chat", help="Chat with Brain")
    p_chat.add_argument("message", nargs="*", help="Message")
    p_chat.add_argument("--stream", "-s", action="store_true", help="Stream response")
    p_chat.add_argument("--model", "-m", help="Model override")

    # status
    sub.add_parser("status", help="System status")

    # list
    sub.add_parser("list", help="List playbooks")

    # health / selftest
    sub.add_parser("health", help="Run self-test")
    sub.add_parser("selftest", help="Run self-test (alias)")

    # models
    sub.add_parser("models", help="List Ollama models")

    # logs
    p_logs = sub.add_parser("logs", help="Show recent logs")
    p_logs.add_argument("--limit", "-n", type=int, default=20, help="Number of logs")

    # daemon
    p_daemon = sub.add_parser("daemon", help="Control daemon")
    p_daemon.add_argument("action", choices=["start", "stop", "status"], help="Action")

    return parser


# ─── Entry Point ────────────────────────────────────────────────


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.api_url:
        import os
        os.environ["MILYFE_API_URL"] = args.api_url

    if not args.command:
        parser.print_help()
        sys.exit(0)

    command_map = {
        "run": cmd_run,
        "chat": lambda a: cmd_chat_stream(a) if getattr(a, "stream", False) else cmd_chat(a),
        "status": cmd_status,
        "list": cmd_list,
        "health": cmd_health,
        "selftest": cmd_health,
        "models": cmd_models,
        "logs": cmd_logs,
        "daemon": cmd_daemon,
    }

    handler = command_map.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        asyncio.run(handler(args))
    except KeyboardInterrupt:
        print(c("\nAborted.", "dim"))
        sys.exit(0)


if __name__ == "__main__":
    main()
