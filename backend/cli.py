"""
MiLyfe Brain - CLI Entry Point

Command-line interface for interacting with the MiLyfe Brain backend.
Supports: run, chat, status, list, health, selftest, models, logs, daemon.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Optional

import httpx


DEFAULT_BASE_URL = "http://localhost:8200"


def get_client(base_url: Optional[str] = None) -> httpx.Client:
    """Create a synchronous HTTP client."""
    return httpx.Client(base_url=base_url or DEFAULT_BASE_URL, timeout=30.0)


def cmd_run(args: argparse.Namespace) -> None:
    """Run a task or playbook."""
    client = get_client(args.base_url)

    if args.file:
        # Load playbook from file
        try:
            with open(args.file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Create playbook from task string
        data = {
            "title": args.task[:80],
            "goal": args.task,
            "priority": 5,
        }

    if args.dry_run:
        print("DRY RUN - Would create playbook:")
        print(json.dumps(data, indent=2))
        return

    resp = client.post("/api/playbooks/", json=data)
    if resp.status_code == 200:
        result = resp.json()
        print(f"Playbook created: {result['id']}")
        print(f"  Title: {result['title']}")
        print(f"  Status: {result['status']}")
        print(f"  Steps: {len(result.get('steps', []))}")

        if not args.no_wait:
            print("\nWaiting for completion...")
            _wait_for_playbook(client, result["id"])
    else:
        print(f"Error: {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)


def cmd_chat(args: argparse.Namespace) -> None:
    """Send a chat message."""
    client = get_client(args.base_url)

    data = {
        "content": args.message,
    }
    if args.model:
        data["model"] = args.model

    if args.stream:
        # Use streaming endpoint
        with client.stream(
            "GET",
            "/api/streaming/chat",
            params={"message": args.message},
        ) as resp:
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "token" in payload:
                        print(payload["token"], end="", flush=True)
                    if payload.get("done"):
                        print()
                        break
    else:
        resp = client.post("/api/chat/send", json=data)
        if resp.status_code == 200:
            result = resp.json()
            print(result.get("content", "No response"))
        else:
            print(f"Error: {resp.status_code} - {resp.text}", file=sys.stderr)
            sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:
    """Show system status."""
    client = get_client(args.base_url)

    resp = client.get("/health")
    if resp.status_code == 200:
        data = resp.json()
        print("MiLyfe Brain Status")
        print("=" * 40)
        print(f"  Status:     {data['status']}")
        print(f"  Version:    {data['version']}")
        print(f"  Uptime:     {data['uptime_seconds']:.0f}s")
        print(f"  Ollama:     {'connected' if data['ollama_connected'] else 'disconnected'}")
        print(f"  ChromaDB:   {'connected' if data['chroma_connected'] else 'disconnected'}")
        print(f"  Redis:      {'connected' if data['redis_connected'] else 'disconnected'}")
        print(f"  Database:   {'connected' if data['database_connected'] else 'disconnected'}")
        print(f"  Agents:     {data['active_agents']}")
    else:
        print(f"Error: Could not connect ({resp.status_code})", file=sys.stderr)
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List playbooks."""
    client = get_client(args.base_url)

    resp = client.get("/api/playbooks/", params={"limit": 20})
    if resp.status_code == 200:
        playbooks = resp.json()
        if not playbooks:
            print("No playbooks found.")
            return

        print(f"{'ID':<12} {'Status':<12} {'Title'}")
        print("-" * 60)
        for pb in playbooks:
            short_id = pb["id"][:10]
            print(f"{short_id:<12} {pb['status']:<12} {pb['title'][:40]}")
    else:
        print(f"Error: {resp.status_code}", file=sys.stderr)
        sys.exit(1)


def cmd_health(args: argparse.Namespace) -> None:
    """Run health check."""
    cmd_status(args)


def cmd_selftest(args: argparse.Namespace) -> None:
    """Run self-tests."""
    client = get_client(args.base_url)

    print("Running self-tests...")
    resp = client.post("/api/selftest/run")
    if resp.status_code == 200:
        report = resp.json()
        print(f"\nResults: {report['passed_count']}/{report['total']} passed")
        print("-" * 40)
        for result in report.get("results", []):
            icon = "PASS" if result["passed"] else "FAIL"
            print(f"  [{icon}] {result['name']}: {result['message']} ({result['duration_ms']:.0f}ms)")

        if not report["passed"]:
            sys.exit(1)
    else:
        print(f"Error: {resp.status_code}", file=sys.stderr)
        sys.exit(1)


def cmd_models(args: argparse.Namespace) -> None:
    """List available models."""
    client = get_client(args.base_url)

    resp = client.get("/api/brain/onboarding/recommend-models")
    if resp.status_code == 200:
        data = resp.json()
        print("Available Models:")
        print("-" * 40)
        for model in data.get("available_models", []):
            print(f"  {model['name']}")

        print("\nCurrent Configuration:")
        config = data.get("current_config", {})
        for key, value in config.items():
            print(f"  {key}: {value}")
    else:
        print(f"Error: {resp.status_code}", file=sys.stderr)
        sys.exit(1)


def cmd_logs(args: argparse.Namespace) -> None:
    """Show recent logs."""
    client = get_client(args.base_url)

    params = {"limit": args.limit}
    resp = client.get("/api/logs/", params=params)
    if resp.status_code == 200:
        logs = resp.json()
        if not logs:
            print("No logs found.")
            return

        for log in logs:
            ts = log.get("timestamp", "")[:19]
            role = log.get("agent_role", "-")
            action = log.get("action_type", "-")
            desc = log.get("description", "")[:60]
            risk = log.get("risk_level", "low")
            print(f"[{ts}] {role:<12} {action:<15} [{risk}] {desc}")
    else:
        print(f"Error: {resp.status_code}", file=sys.stderr)
        sys.exit(1)


def cmd_daemon(args: argparse.Namespace) -> None:
    """Control the daemon."""
    client = get_client(args.base_url)

    if args.action == "start":
        resp = client.post("/api/daemon/start")
    elif args.action == "stop":
        resp = client.post("/api/daemon/stop")
    elif args.action == "status":
        resp = client.get("/api/daemon/status")
    else:
        print(f"Unknown action: {args.action}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 200:
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"Error: {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)


def _wait_for_playbook(client: httpx.Client, playbook_id: str) -> None:
    """Poll playbook status until completion."""
    import time

    while True:
        resp = client.get(f"/api/playbooks/{playbook_id}/status")
        if resp.status_code != 200:
            print(f"\nError checking status: {resp.status_code}")
            break

        status = resp.json()
        progress = status.get("progress_percent", 0)
        state = status.get("status", "unknown")

        print(f"\r  Progress: {progress:.0f}% ({state})", end="", flush=True)

        if state in ("completed", "failed", "cancelled"):
            print(f"\n  Final status: {state}")
            break

        time.sleep(2)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="milyfe",
        description="MiLyfe Brain CLI - AI agent swarm orchestration",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Backend base URL (default: {DEFAULT_BASE_URL})",
    )

    subparsers = parser.add_subparsers(dest="command")

    # milyfe run
    run_parser = subparsers.add_parser("run", help="Run a task or playbook")
    run_parser.add_argument("task", nargs="?", default="", help="Task description")
    run_parser.add_argument("--file", "-f", help="Load playbook from JSON file")
    run_parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    run_parser.add_argument("--no-wait", action="store_true", help="Don't wait for completion")

    # milyfe chat
    chat_parser = subparsers.add_parser("chat", help="Send a chat message")
    chat_parser.add_argument("message", help="Message content")
    chat_parser.add_argument("--stream", action="store_true", help="Stream response tokens")
    chat_parser.add_argument("--model", help="Override model for this message")

    # milyfe status
    subparsers.add_parser("status", help="Show system status")

    # milyfe list
    subparsers.add_parser("list", help="List playbooks")

    # milyfe health
    subparsers.add_parser("health", help="Run health check")

    # milyfe selftest
    subparsers.add_parser("selftest", help="Run connectivity self-tests")

    # milyfe models
    subparsers.add_parser("models", help="List available models")

    # milyfe logs
    logs_parser = subparsers.add_parser("logs", help="Show recent action logs")
    logs_parser.add_argument("--limit", type=int, default=20, help="Number of entries")

    # milyfe daemon
    daemon_parser = subparsers.add_parser("daemon", help="Control background daemon")
    daemon_parser.add_argument("action", choices=["start", "stop", "status"], help="Daemon action")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "run": cmd_run,
        "chat": cmd_chat,
        "status": cmd_status,
        "list": cmd_list,
        "health": cmd_health,
        "selftest": cmd_selftest,
        "models": cmd_models,
        "logs": cmd_logs,
        "daemon": cmd_daemon,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except httpx.ConnectError:
            print(
                f"Error: Cannot connect to MiLyfe Brain at {args.base_url}",
                file=sys.stderr,
            )
            print("Is the server running? Start with: uvicorn main:app", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
