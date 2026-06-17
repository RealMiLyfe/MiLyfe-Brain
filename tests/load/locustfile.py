"""
MiLyfe Brain Load Tests using Locust.

Usage:
    # Interactive mode (web UI):
    locust -f locustfile.py --host=http://localhost:8200

    # Headless mode (CI):
    locust -f locustfile.py --headless -u 50 -r 5 --run-time 300s \
        --host=http://localhost:8200 --csv=results

    # Specific user class:
    locust -f locustfile.py --headless -u 20 -r 2 --run-time 60s \
        --host=http://localhost:8200 ReadHeavyUser
"""

import json
import random
import uuid
from typing import Optional

from locust import HttpUser, between, events, tag, task
from locust.runners import MasterRunner


# ─── Test Data ────────────────────────────────────────────────────────

PLAYBOOK_TITLES = [
    "Build a REST API",
    "Create a landing page",
    "Write unit tests",
    "Refactor authentication module",
    "Deploy to staging",
    "Generate API documentation",
    "Fix memory leak in worker",
    "Add error handling to payment flow",
    "Create database migration",
    "Implement search feature",
]

CHAT_MESSAGES = [
    "Explain how the agent swarm works",
    "What models are available?",
    "Help me debug this Python error",
    "Create a new React component for user profiles",
    "What playbooks have been run today?",
    "Show me the file structure of the workspace",
    "How do I add a new tool to the registry?",
    "Summarize the last playbook execution",
    "What are the current safety settings?",
    "Run a quick health check on all services",
]

AGENT_ROLES = [
    "orchestrator", "researcher", "coder", "executor",
    "critic", "designer", "writer", "debugger", "planner",
]


# ─── Event Hooks ──────────────────────────────────────────────────────

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize test state."""
    if isinstance(environment.runner, MasterRunner):
        print("Running as master node")


# ─── User Classes ─────────────────────────────────────────────────────

class ReadHeavyUser(HttpUser):
    """Simulates a user primarily reading/browsing the system.
    70% of real traffic pattern.
    """
    weight = 7
    wait_time = between(1, 3)

    def on_start(self):
        """Setup: create a session."""
        self.session_id = str(uuid.uuid4())
        self.playbook_ids: list = []

    @tag("health")
    @task(10)
    def health_check(self):
        """GET /health - Most frequent request."""
        self.client.get("/health", name="/health")

    @tag("playbooks", "read")
    @task(8)
    def list_playbooks(self):
        """GET /api/playbooks/ - List playbooks."""
        self.client.get("/api/playbooks/", name="/api/playbooks/ [list]")

    @tag("agents", "read")
    @task(6)
    def list_active_agents(self):
        """GET /api/agents/active - Check active agents."""
        self.client.get("/api/agents/active", name="/api/agents/active")

    @tag("agents", "read")
    @task(4)
    def list_agent_roles(self):
        """GET /api/agents/roles - Available roles."""
        self.client.get("/api/agents/roles", name="/api/agents/roles")

    @tag("queue", "read")
    @task(5)
    def queue_status(self):
        """GET /api/queue/status - Queue state."""
        self.client.get("/api/queue/status", name="/api/queue/status")

    @tag("notifications", "read")
    @task(3)
    def get_notifications(self):
        """GET /api/notifications/ - Unread notifications."""
        self.client.get(
            "/api/notifications/",
            params={"unread_only": "true"},
            name="/api/notifications/",
        )

    @tag("tokens", "read")
    @task(2)
    def token_stats(self):
        """GET /api/tokens/stats - Usage statistics."""
        self.client.get(
            "/api/tokens/stats",
            params={"days": 7},
            name="/api/tokens/stats",
        )

    @tag("logs", "read")
    @task(3)
    def get_logs(self):
        """GET /api/logs/ - Action logs."""
        self.client.get(
            "/api/logs/",
            params={"limit": 50},
            name="/api/logs/",
        )

    @tag("workspace", "read")
    @task(2)
    def workspace_tree(self):
        """GET /api/workspace/tree - File tree."""
        self.client.get("/api/workspace/tree", name="/api/workspace/tree")

    @tag("settings", "read")
    @task(1)
    def get_settings(self):
        """GET /api/settings/ - Current settings."""
        self.client.get("/api/settings/", name="/api/settings/")

    @tag("brain", "read")
    @task(2)
    def brain_status(self):
        """GET /api/brain/daemon/status - Daemon status."""
        self.client.get("/api/brain/daemon/status", name="/api/brain/daemon/status")

    @tag("playbooks", "read")
    @task(3)
    def get_playbook_status(self):
        """GET /api/playbooks/{id}/status - If we have any."""
        if self.playbook_ids:
            pid = random.choice(self.playbook_ids)
            self.client.get(
                f"/api/playbooks/{pid}/status",
                name="/api/playbooks/[id]/status",
            )


class WriteHeavyUser(HttpUser):
    """Simulates a user actively creating playbooks and chatting.
    20% of real traffic pattern.
    """
    weight = 2
    wait_time = between(2, 5)

    def on_start(self):
        self.session_id = str(uuid.uuid4())
        self.playbook_ids: list = []

    @tag("playbooks", "write")
    @task(5)
    def create_playbook(self):
        """POST /api/playbooks/ - Create a new playbook."""
        payload = {
            "title": random.choice(PLAYBOOK_TITLES),
            "description": f"Automated load test playbook - {uuid.uuid4().hex[:8]}",
            "auto_execute": False,  # Don't actually execute during load test
        }
        with self.client.post(
            "/api/playbooks/",
            json=payload,
            name="/api/playbooks/ [create]",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.playbook_ids.append(data.get("id"))
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Unexpected: {response.status_code}")

    @tag("chat", "write")
    @task(8)
    def send_chat_message(self):
        """POST /api/chat/send - Chat interaction."""
        payload = {
            "message": random.choice(CHAT_MESSAGES),
            "session_id": self.session_id,
        }
        with self.client.post(
            "/api/chat/send",
            json=payload,
            name="/api/chat/send",
            catch_response=True,
            timeout=60,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            elif response.status_code == 503:
                response.failure("Ollama unavailable")
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("chat", "read")
    @task(3)
    def get_chat_history(self):
        """GET /api/chat/history/{session_id} - Retrieve history."""
        self.client.get(
            f"/api/chat/history/{self.session_id}",
            name="/api/chat/history/[session_id]",
        )

    @tag("documents", "write")
    @task(1)
    def search_documents(self):
        """POST /api/documents/search - Semantic search."""
        payload = {
            "query": "How to implement authentication",
            "n_results": 5,
        }
        self.client.post(
            "/api/documents/search",
            json=payload,
            name="/api/documents/search",
        )

    @tag("agents", "write")
    @task(2)
    def spawn_agent(self):
        """POST /api/agents/spawn - Spawn an agent."""
        payload = {
            "role": random.choice(AGENT_ROLES),
            "task": "Load test task - analyze code quality",
        }
        self.client.post(
            "/api/agents/spawn",
            json=payload,
            name="/api/agents/spawn",
        )


class BurstUser(HttpUser):
    """Simulates burst traffic - rapid requests in succession.
    10% of traffic pattern - stress testing.
    """
    weight = 1
    wait_time = between(0.1, 0.5)

    @tag("health", "burst")
    @task(20)
    def rapid_health(self):
        """Rapid health checks simulating monitoring."""
        self.client.get("/health", name="/health [burst]")

    @tag("playbooks", "burst")
    @task(5)
    def rapid_list(self):
        """Rapid list requests."""
        self.client.get("/api/playbooks/", name="/api/playbooks/ [burst]")

    @tag("agents", "burst")
    @task(5)
    def rapid_agents(self):
        """Rapid agent list."""
        self.client.get("/api/agents/active", name="/api/agents/active [burst]")

    @tag("queue", "burst")
    @task(3)
    def rapid_queue(self):
        """Rapid queue checks."""
        self.client.get("/api/queue/status", name="/api/queue/status [burst]")
