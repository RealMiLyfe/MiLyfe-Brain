"""
User Intent Engine - Clarify ambiguity before executing.

Analyzes user input to detect ambiguity, missing context, or risky assumptions.
Asks clarifying questions before committing to execution.

Features:
- Ambiguity detection (multiple valid interpretations)
- Missing context identification
- Risk assessment (destructive actions need confirmation)
- Assumption surfacing (what the system infers)
- Confidence scoring
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IntentConfidence(str, Enum):
    HIGH = "high"          # >90% - proceed automatically
    MEDIUM = "medium"      # 60-90% - proceed with notification
    LOW = "low"            # 30-60% - ask for clarification
    AMBIGUOUS = "ambiguous"  # <30% - must clarify


@dataclass
class ClarificationQuestion:
    """A question to ask the user for clarification."""
    id: str
    question: str
    options: List[str] = field(default_factory=list)
    required: bool = True
    context: str = ""


@dataclass
class IntentAnalysis:
    """Result of intent analysis."""
    original_input: str
    detected_intent: str
    confidence: IntentConfidence
    assumptions: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    clarifications_needed: List[ClarificationQuestion] = field(default_factory=list)
    risk_level: str = "low"
    suggested_interpretation: str = ""
    proceed: bool = True


class IntentEngine:
    """Analyzes user intent and surfaces ambiguity before execution."""

    # Patterns that suggest ambiguity
    AMBIGUOUS_PATTERNS = [
        (r"\b(it|this|that|these|those)\b", "pronoun_reference"),
        (r"\b(the file|the code|the app)\b", "vague_reference"),
        (r"\b(fix|improve|update|change)\b(?!.*\b(by|to|with)\b)", "vague_action"),
        (r"\b(everything|all|each)\b", "scope_unclear"),
        (r"\b(maybe|perhaps|possibly|might)\b", "uncertain_intent"),
        (r"\b(or|either)\b", "multiple_options"),
    ]

    # Patterns indicating destructive/risky operations
    RISK_PATTERNS = [
        (r"\b(delete|remove|drop|destroy|wipe|reset)\b", "destructive"),
        (r"\b(deploy|push|publish|release)\b", "deployment"),
        (r"\b(all files|entire|everything)\b", "broad_scope"),
        (r"\b(production|prod|live)\b", "production_target"),
    ]

    def __init__(self):
        self._context_history: List[Dict] = []

    async def analyze(self, user_input: str, context: Optional[Dict] = None) -> IntentAnalysis:
        """Analyze user intent and detect ambiguity."""
        analysis = IntentAnalysis(
            original_input=user_input,
            detected_intent="",
            confidence=IntentConfidence.HIGH,
        )

        # Check for ambiguities
        ambiguities = self._detect_ambiguities(user_input)
        analysis.ambiguities = ambiguities

        # Check for risks
        risks = self._detect_risks(user_input)
        if risks:
            analysis.risk_level = "high" if "destructive" in risks or "production_target" in risks else "medium"

        # Determine confidence
        if len(ambiguities) >= 3:
            analysis.confidence = IntentConfidence.AMBIGUOUS
        elif len(ambiguities) >= 1:
            analysis.confidence = IntentConfidence.LOW
        elif risks:
            analysis.confidence = IntentConfidence.MEDIUM
        else:
            analysis.confidence = IntentConfidence.HIGH

        # Generate clarification questions
        analysis.clarifications_needed = self._generate_clarifications(user_input, ambiguities, risks)

        # Determine if we should proceed or ask
        analysis.proceed = (
            analysis.confidence in (IntentConfidence.HIGH, IntentConfidence.MEDIUM)
            and analysis.risk_level != "high"
        )

        # Surface assumptions
        analysis.assumptions = self._surface_assumptions(user_input, context)

        # Store for context
        self._context_history.append({
            "input": user_input,
            "confidence": analysis.confidence.value,
            "proceed": analysis.proceed,
        })

        return analysis

    def _detect_ambiguities(self, text: str) -> List[str]:
        """Detect ambiguous patterns in input."""
        found = []
        for pattern, category in self.AMBIGUOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(category)
        return found

    def _detect_risks(self, text: str) -> List[str]:
        """Detect risky patterns in input."""
        found = []
        for pattern, category in self.RISK_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(category)
        return found

    def _generate_clarifications(self, text: str, ambiguities: List[str], risks: List[str]) -> List[ClarificationQuestion]:
        """Generate clarification questions based on detected issues."""
        questions = []

        if "pronoun_reference" in ambiguities:
            questions.append(ClarificationQuestion(
                id="pronoun_ref",
                question="What specifically are you referring to?",
                context="Your request uses pronouns (it/this/that) without a clear referent.",
            ))

        if "vague_reference" in ambiguities:
            questions.append(ClarificationQuestion(
                id="which_file",
                question="Which specific file or component?",
                context="Multiple files/components could match your description.",
            ))

        if "vague_action" in ambiguities:
            questions.append(ClarificationQuestion(
                id="action_details",
                question="How should this be done? Any specific approach?",
                options=["Best practices", "Minimal changes", "Complete rewrite", "Let me specify"],
            ))

        if "scope_unclear" in ambiguities:
            questions.append(ClarificationQuestion(
                id="scope",
                question="What's the scope of this change?",
                options=["Current file only", "Current directory", "Entire project", "Let me specify"],
            ))

        if "destructive" in risks:
            questions.append(ClarificationQuestion(
                id="confirm_destructive",
                question="This involves destructive changes. Are you sure?",
                options=["Yes, proceed", "No, cancel", "Show me what will be affected first"],
                required=True,
            ))

        if "production_target" in risks:
            questions.append(ClarificationQuestion(
                id="confirm_production",
                question="This targets production. Please confirm this is intentional.",
                options=["Yes, deploy to production", "No, use staging", "Cancel"],
                required=True,
            ))

        return questions

    def _surface_assumptions(self, text: str, context: Optional[Dict]) -> List[str]:
        """Surface assumptions the system is making."""
        assumptions = []

        if not context or "workspace" not in context:
            assumptions.append("Assuming current workspace directory")

        if "test" not in text.lower() and any(w in text.lower() for w in ["write", "create", "build"]):
            assumptions.append("Will create in workspace root unless specified otherwise")

        if "model" not in text.lower():
            assumptions.append("Using default model for this task complexity")

        return assumptions

    async def resolve_clarification(self, analysis: IntentAnalysis, answers: Dict[str, str]) -> IntentAnalysis:
        """Resolve clarifications with user answers and update analysis."""
        # Remove answered clarifications
        analysis.clarifications_needed = [
            q for q in analysis.clarifications_needed
            if q.id not in answers
        ]

        # Update confidence
        if not analysis.clarifications_needed:
            analysis.confidence = IntentConfidence.HIGH
            analysis.proceed = True

        # Enrich the original input with answers
        enrichment = " ".join(f"[{k}: {v}]" for k, v in answers.items())
        analysis.suggested_interpretation = f"{analysis.original_input} {enrichment}"

        return analysis


# Singleton
intent_engine = IntentEngine()
