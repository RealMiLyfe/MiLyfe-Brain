"""MiLyfe Brain — Agent Learning & Self-Improvement Service.

Learn from corrections, develop specialization, track failure patterns,
adapt behavior based on workspace context, improve prompts over time.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog

from models.schemas import AgentRole

logger = structlog.get_logger()


# ─── Learning Entry Types ───────────────────────────────────────


class CorrectionEntry:
    """A user correction that an agent should learn from."""

    def __init__(
        self,
        agent_role: AgentRole,
        original_output: str,
        correction: str,
        context: str = "",
        timestamp: Optional[datetime] = None,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.agent_role = agent_role
        self.original_output = original_output[:500]
        self.correction = correction
        self.context = context[:300]
        self.timestamp = timestamp or datetime.utcnow()
        self.applied_count: int = 0

    def to_prompt_instruction(self) -> str:
        """Convert to a prompt instruction for the agent."""
        return f"When asked about '{self.context[:50]}...': {self.correction}"


class FailurePattern:
    """A recognized pattern of agent failures."""

    def __init__(
        self,
        agent_role: AgentRole,
        error_signature: str,
        context_pattern: str,
        fix_strategy: str = "",
    ):
        self.id = str(uuid.uuid4())[:8]
        self.agent_role = agent_role
        self.error_signature = error_signature
        self.context_pattern = context_pattern
        self.fix_strategy = fix_strategy
        self.occurrence_count: int = 1
        self.last_seen: datetime = datetime.utcnow()
        self.resolved: bool = False


class Specialization:
    """An agent's developed expertise area."""

    def __init__(self, agent_role: AgentRole, domain: str, confidence: float = 0.5):
        self.agent_role = agent_role
        self.domain = domain
        self.confidence = confidence  # 0.0 to 1.0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.last_used: datetime = datetime.utcnow()

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    def record_outcome(self, success: bool):
        if success:
            self.success_count += 1
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            self.failure_count += 1
            self.confidence = max(0.0, self.confidence - 0.1)
        self.last_used = datetime.utcnow()


# ─── Agent Learning Service ─────────────────────────────────────


class AgentLearningService:
    """Manages agent learning, adaptation, and self-improvement.

    Capabilities:
    1. Learn from user corrections (remember "do it THIS way")
    2. Track failure patterns (same error → develop prevention strategy)
    3. Develop specializations (get better at specific domains over time)
    4. Adaptive prompt enhancement (inject learned knowledge into prompts)
    5. Performance tracking per role per domain
    6. Cross-agent knowledge transfer
    """

    def __init__(self):
        # Corrections: role -> [CorrectionEntry]
        self._corrections: Dict[AgentRole, List[CorrectionEntry]] = defaultdict(list)

        # Failure patterns: role -> [FailurePattern]
        self._failure_patterns: Dict[AgentRole, List[FailurePattern]] = defaultdict(list)

        # Specializations: role -> domain -> Specialization
        self._specializations: Dict[AgentRole, Dict[str, Specialization]] = defaultdict(dict)

        # Performance history: role -> [(success: bool, domain: str, timestamp)]
        self._performance_history: Dict[AgentRole, List[Tuple[bool, str, datetime]]] = defaultdict(list)

        # Prompt enhancements learned over time
        self._prompt_enhancements: Dict[AgentRole, List[str]] = defaultdict(list)

        # Domain detection keywords
        self._domain_keywords: Dict[str, List[str]] = {
            "api": ["api", "endpoint", "rest", "route", "http", "request", "response"],
            "database": ["sql", "database", "query", "migration", "schema", "table", "orm"],
            "frontend": ["react", "component", "css", "html", "ui", "ux", "layout", "style"],
            "testing": ["test", "assert", "mock", "fixture", "spec", "coverage"],
            "devops": ["docker", "deploy", "ci", "cd", "pipeline", "kubernetes", "container"],
            "security": ["auth", "token", "password", "encrypt", "permission", "vulnerability"],
            "performance": ["optimize", "cache", "fast", "slow", "latency", "memory", "cpu"],
            "python": ["python", "pip", "venv", "django", "fastapi", "flask", "pytest"],
            "javascript": ["node", "npm", "react", "next", "typescript", "webpack", "eslint"],
            "documentation": ["readme", "docs", "docstring", "comment", "explain", "guide"],
        }

    # ─── User Corrections ───────────────────────────────────────

    def record_correction(
        self,
        agent_role: AgentRole,
        original_output: str,
        correction: str,
        context: str = "",
    ) -> str:
        """Record a user correction for an agent to learn from."""
        entry = CorrectionEntry(
            agent_role=agent_role,
            original_output=original_output,
            correction=correction,
            context=context,
        )
        self._corrections[agent_role].append(entry)

        # Keep bounded (last 50 corrections per role)
        if len(self._corrections[agent_role]) > 50:
            self._corrections[agent_role] = self._corrections[agent_role][-50:]

        # Also create a prompt enhancement
        self._prompt_enhancements[agent_role].append(
            f"User correction: {correction[:100]}"
        )

        logger.info("correction_recorded", role=agent_role.value, correction=correction[:50])
        return entry.id

    def get_corrections_for_prompt(self, agent_role: AgentRole, task: str = "", limit: int = 5) -> str:
        """Get relevant corrections formatted for prompt injection."""
        corrections = self._corrections.get(agent_role, [])
        if not corrections:
            return ""

        # Find relevant corrections based on task similarity
        if task:
            task_words = set(task.lower().split())
            scored = []
            for c in corrections:
                context_words = set(c.context.lower().split())
                overlap = len(task_words & context_words)
                scored.append((overlap, c))
            scored.sort(key=lambda x: -x[0])
            relevant = [c for score, c in scored[:limit] if score > 0]
        else:
            relevant = corrections[-limit:]

        if not relevant:
            return ""

        lines = ["[Learned from user corrections — ALWAYS apply these]"]
        for c in relevant:
            c.applied_count += 1
            lines.append(f"- {c.correction}")

        return "\n".join(lines)

    # ─── Failure Patterns ───────────────────────────────────────

    def record_failure(
        self,
        agent_role: AgentRole,
        error_message: str,
        task_context: str = "",
    ):
        """Record a failure to detect patterns."""
        # Create error signature (normalize the error)
        sig = self._create_error_signature(error_message)

        # Check if pattern already exists
        existing = None
        for pattern in self._failure_patterns[agent_role]:
            if pattern.error_signature == sig:
                existing = pattern
                break

        if existing:
            existing.occurrence_count += 1
            existing.last_seen = datetime.utcnow()
        else:
            self._failure_patterns[agent_role].append(FailurePattern(
                agent_role=agent_role,
                error_signature=sig,
                context_pattern=task_context[:200],
            ))

        # Track performance
        domain = self._detect_domain(task_context)
        self._performance_history[agent_role].append((False, domain, datetime.utcnow()))

        # Bound history
        if len(self._performance_history[agent_role]) > 200:
            self._performance_history[agent_role] = self._performance_history[agent_role][-200:]

    def record_success(self, agent_role: AgentRole, task_context: str = ""):
        """Record a successful execution."""
        domain = self._detect_domain(task_context)
        self._performance_history[agent_role].append((True, domain, datetime.utcnow()))

        # Update specialization
        if domain:
            if domain not in self._specializations[agent_role]:
                self._specializations[agent_role][domain] = Specialization(agent_role, domain)
            self._specializations[agent_role][domain].record_outcome(True)

    def get_failure_prevention_prompt(self, agent_role: AgentRole, task: str = "") -> str:
        """Get failure prevention instructions based on known patterns."""
        patterns = self._failure_patterns.get(agent_role, [])
        if not patterns:
            return ""

        # Find patterns that might apply to this task
        frequent = sorted(patterns, key=lambda p: -p.occurrence_count)[:3]
        if not frequent or frequent[0].occurrence_count < 2:
            return ""

        lines = ["[Known failure patterns — avoid these]"]
        for p in frequent:
            if p.occurrence_count >= 2:
                lines.append(f"- Error seen {p.occurrence_count}x: {p.error_signature[:80]}")
                if p.fix_strategy:
                    lines.append(f"  Fix: {p.fix_strategy}")

        return "\n".join(lines)

    def suggest_fix_strategy(self, agent_role: AgentRole, error_signature: str, strategy: str):
        """Record a fix strategy for a known failure pattern."""
        for pattern in self._failure_patterns.get(agent_role, []):
            if pattern.error_signature == error_signature:
                pattern.fix_strategy = strategy
                pattern.resolved = True
                break

    # ─── Specialization ─────────────────────────────────────────

    def get_specialization_context(self, agent_role: AgentRole, task: str) -> str:
        """Get specialization context for an agent based on the task domain."""
        domain = self._detect_domain(task)
        if not domain:
            return ""

        specs = self._specializations.get(agent_role, {})
        spec = specs.get(domain)

        if not spec:
            return ""

        if spec.confidence > 0.7:
            return f"[Specialization: You have high expertise in {domain} (confidence: {spec.confidence:.0%}, {spec.success_count} successes)]"
        elif spec.confidence < 0.3:
            return f"[Caution: You have struggled with {domain} tasks before (success rate: {spec.success_rate:.0%}). Be extra careful and thorough.]"

        return ""

    def get_best_role_for_domain(self, domain: str) -> Optional[AgentRole]:
        """Find the best agent role for a given domain based on performance."""
        best_role = None
        best_confidence = 0.0

        for role, specs in self._specializations.items():
            spec = specs.get(domain)
            if spec and spec.confidence > best_confidence:
                best_confidence = spec.confidence
                best_role = role

        return best_role

    # ─── Full Learning Context ──────────────────────────────────

    def get_learning_context(self, agent_role: AgentRole, task: str) -> str:
        """Get the full learning context to inject into an agent's prompt.

        Combines corrections, failure prevention, and specialization.
        """
        parts = []

        # Corrections
        corrections = self.get_corrections_for_prompt(agent_role, task)
        if corrections:
            parts.append(corrections)

        # Failure prevention
        prevention = self.get_failure_prevention_prompt(agent_role, task)
        if prevention:
            parts.append(prevention)

        # Specialization
        spec_ctx = self.get_specialization_context(agent_role, task)
        if spec_ctx:
            parts.append(spec_ctx)

        # Prompt enhancements
        enhancements = self._prompt_enhancements.get(agent_role, [])[-3:]
        if enhancements:
            parts.append("[Learned preferences]\n" + "\n".join(f"- {e}" for e in enhancements))

        return "\n\n".join(parts)

    # ─── Analytics ──────────────────────────────────────────────

    def get_performance_report(self) -> Dict[str, Any]:
        """Get a full performance report across all agents."""
        report = {}
        for role in AgentRole:
            history = self._performance_history.get(role, [])
            if not history:
                continue

            successes = sum(1 for s, _, _ in history if s)
            total = len(history)

            # Domain breakdown
            domain_stats: Dict[str, Dict] = defaultdict(lambda: {"success": 0, "total": 0})
            for success, domain, _ in history:
                domain_stats[domain]["total"] += 1
                if success:
                    domain_stats[domain]["success"] += 1

            report[role.value] = {
                "total_tasks": total,
                "successes": successes,
                "failures": total - successes,
                "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
                "corrections_received": len(self._corrections.get(role, [])),
                "failure_patterns": len(self._failure_patterns.get(role, [])),
                "specializations": {
                    domain: {
                        "confidence": spec.confidence,
                        "success_rate": spec.success_rate,
                    }
                    for domain, spec in self._specializations.get(role, {}).items()
                },
                "domain_performance": {
                    d: round(s["success"] / s["total"] * 100, 1) if s["total"] > 0 else 0
                    for d, s in domain_stats.items()
                },
            }

        return report

    def get_improvement_suggestions(self) -> List[Dict]:
        """Suggest improvements based on performance data."""
        suggestions = []

        for role in AgentRole:
            history = self._performance_history.get(role, [])
            if len(history) < 5:
                continue

            # Check for declining performance
            recent = history[-10:]
            older = history[-20:-10] if len(history) >= 20 else []

            recent_rate = sum(1 for s, _, _ in recent if s) / len(recent)
            older_rate = sum(1 for s, _, _ in older if s) / len(older) if older else recent_rate

            if recent_rate < older_rate - 0.2:
                suggestions.append({
                    "role": role.value,
                    "type": "declining_performance",
                    "message": f"{role.value} success rate dropped from {older_rate:.0%} to {recent_rate:.0%}",
                    "suggestion": "Consider adjusting prompts or switching models for this role",
                })

            # Check frequent failures
            patterns = self._failure_patterns.get(role, [])
            unresolved = [p for p in patterns if not p.resolved and p.occurrence_count >= 3]
            for p in unresolved:
                suggestions.append({
                    "role": role.value,
                    "type": "recurring_failure",
                    "message": f"Error occurs repeatedly ({p.occurrence_count}x): {p.error_signature[:60]}",
                    "suggestion": "Needs a fix strategy or prompt adjustment",
                })

        return suggestions

    # ─── Cross-Agent Knowledge Transfer ─────────────────────────

    def transfer_knowledge(self, from_role: AgentRole, to_role: AgentRole, domain: str):
        """Transfer learned knowledge from one agent role to another."""
        # Transfer relevant corrections
        source_corrections = [
            c for c in self._corrections.get(from_role, [])
            if domain.lower() in c.context.lower()
        ]
        for c in source_corrections[-5:]:
            transferred = CorrectionEntry(
                agent_role=to_role,
                original_output=c.original_output,
                correction=f"(From {from_role.value}): {c.correction}",
                context=c.context,
            )
            self._corrections[to_role].append(transferred)

        logger.info("knowledge_transferred", from_role=from_role.value, to_role=to_role.value, domain=domain)

    # ─── Helpers ────────────────────────────────────────────────

    def _detect_domain(self, text: str) -> str:
        """Detect the domain of a task/context."""
        if not text:
            return "general"

        text_lower = text.lower()
        scores: Counter = Counter()

        for domain, keywords in self._domain_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[domain] += 1

        if scores:
            return scores.most_common(1)[0][0]
        return "general"

    def _create_error_signature(self, error: str) -> str:
        """Create a normalized error signature for pattern matching."""
        # Remove specific file paths, line numbers, variable values
        import re
        normalized = re.sub(r"line \d+", "line N", error)
        normalized = re.sub(r"'[^']{20,}'", "'...'", normalized)
        normalized = re.sub(r"/[\w/]+\.\w+", "<path>", normalized)
        normalized = re.sub(r"\b\d{4,}\b", "N", normalized)

        # Take first 100 chars as signature
        return normalized[:100].strip()


# Singleton
agent_learning = AgentLearningService()
