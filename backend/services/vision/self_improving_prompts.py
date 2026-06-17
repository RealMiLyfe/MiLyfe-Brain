"""
Self-Improving Prompts - A/B testing and auto few-shot generation.

Continuously optimizes agent prompts based on execution outcomes.
Tracks which prompt variants produce better results and automatically
generates few-shot examples from successful executions.

Features:
- Prompt variant A/B testing
- Automatic quality scoring
- Few-shot example generation from successes
- Prompt evolution (mutate successful prompts)
- Regression detection
"""

import hashlib
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PromptVariant:
    """A prompt variant being tested."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    variant_label: str = "A"  # A, B, C, ...
    prompt_text: str = ""
    success_count: int = 0
    failure_count: int = 0
    total_uses: int = 0
    avg_quality_score: float = 0.0
    avg_tokens_used: float = 0.0
    avg_duration_ms: float = 0.0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        if self.total_uses == 0:
            return 0.0
        return self.success_count / self.total_uses

    @property
    def confidence(self) -> float:
        """Statistical confidence based on sample size."""
        if self.total_uses < 10:
            return 0.0
        return min(1.0, self.total_uses / 100)


@dataclass
class FewShotExample:
    """An auto-generated few-shot example."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    input_text: str = ""
    output_text: str = ""
    quality_score: float = 0.0
    times_used: int = 0
    source_playbook_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class SelfImprovingPrompts:
    """Manages prompt optimization and few-shot generation."""

    def __init__(self):
        self._variants: Dict[str, List[PromptVariant]] = {}
        self._few_shots: Dict[str, List[FewShotExample]] = {}
        self._experiment_traffic: Dict[str, float] = {}  # name → % traffic to variant B

    def register_prompt(self, name: str, base_prompt: str, variants: Optional[List[str]] = None):
        """Register a prompt for optimization."""
        self._variants[name] = [
            PromptVariant(name=name, variant_label="A", prompt_text=base_prompt)
        ]
        if variants:
            for i, v in enumerate(variants):
                self._variants[name].append(
                    PromptVariant(name=name, variant_label=chr(66 + i), prompt_text=v)
                )
        self._experiment_traffic[name] = 0.2  # 20% to variant B initially

    def select_variant(self, name: str) -> Tuple[str, str]:
        """Select a prompt variant using Thompson Sampling.

        Returns (variant_id, prompt_text)
        """
        variants = self._variants.get(name, [])
        if not variants:
            return "", ""

        if len(variants) == 1:
            v = variants[0]
            v.total_uses += 1
            return v.id, v.prompt_text

        # Thompson Sampling: sample from Beta distribution
        scores = []
        for v in variants:
            if not v.is_active:
                scores.append(-1)
                continue
            # Beta(successes + 1, failures + 1)
            alpha = v.success_count + 1
            beta = v.failure_count + 1
            score = random.betavariate(alpha, beta)
            scores.append(score)

        best_idx = scores.index(max(scores))
        selected = variants[best_idx]
        selected.total_uses += 1
        return selected.id, selected.prompt_text

    def record_outcome(
        self,
        name: str,
        variant_id: str,
        success: bool,
        quality_score: float = 0.0,
        tokens_used: int = 0,
        duration_ms: float = 0.0,
        input_text: str = "",
        output_text: str = "",
    ):
        """Record the outcome of using a prompt variant."""
        variants = self._variants.get(name, [])
        for v in variants:
            if v.id == variant_id:
                if success:
                    v.success_count += 1
                else:
                    v.failure_count += 1

                # Update running averages
                n = v.total_uses
                v.avg_quality_score = ((v.avg_quality_score * (n - 1)) + quality_score) / n
                v.avg_tokens_used = ((v.avg_tokens_used * (n - 1)) + tokens_used) / n
                v.avg_duration_ms = ((v.avg_duration_ms * (n - 1)) + duration_ms) / n

                # Auto-generate few-shot if high quality
                if success and quality_score >= 0.8 and input_text and output_text:
                    self._generate_few_shot(name, input_text, output_text, quality_score)

                break

        # Check if we should retire underperforming variants
        self._prune_variants(name)

    def _generate_few_shot(self, category: str, input_text: str, output_text: str, quality: float):
        """Auto-generate a few-shot example from a successful execution."""
        if category not in self._few_shots:
            self._few_shots[category] = []

        # Avoid duplicates
        for existing in self._few_shots[category]:
            if self._similarity(existing.input_text, input_text) > 0.9:
                return

        example = FewShotExample(
            category=category,
            input_text=input_text,
            output_text=output_text,
            quality_score=quality,
        )
        self._few_shots[category].append(example)

        # Keep only top N examples per category
        self._few_shots[category].sort(key=lambda x: x.quality_score, reverse=True)
        self._few_shots[category] = self._few_shots[category][:20]

    def get_few_shots(self, category: str, count: int = 3) -> List[FewShotExample]:
        """Get the best few-shot examples for a category."""
        examples = self._few_shots.get(category, [])
        # Select diverse, high-quality examples
        selected = examples[:count]
        for ex in selected:
            ex.times_used += 1
        return selected

    def _prune_variants(self, name: str):
        """Retire variants that are clearly underperforming."""
        variants = self._variants.get(name, [])
        if len(variants) <= 1:
            return

        # Need minimum sample size
        active = [v for v in variants if v.is_active and v.total_uses >= 30]
        if len(active) < 2:
            return

        # Find the best performer
        best = max(active, key=lambda v: v.success_rate)

        # Retire variants significantly worse than best
        for v in active:
            if v.id != best.id:
                if v.success_rate < best.success_rate * 0.7 and v.confidence > 0.5:
                    v.is_active = False

    def _similarity(self, a: str, b: str) -> float:
        """Simple text similarity (jaccard on words)."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def get_stats(self, name: str) -> Dict[str, Any]:
        """Get optimization stats for a prompt."""
        variants = self._variants.get(name, [])
        return {
            "prompt_name": name,
            "variants": [
                {
                    "label": v.variant_label,
                    "active": v.is_active,
                    "total_uses": v.total_uses,
                    "success_rate": round(v.success_rate, 3),
                    "avg_quality": round(v.avg_quality_score, 3),
                    "avg_tokens": round(v.avg_tokens_used),
                    "confidence": round(v.confidence, 2),
                }
                for v in variants
            ],
            "few_shot_count": len(self._few_shots.get(name, [])),
        }

    def evolve_prompt(self, name: str) -> Optional[str]:
        """Generate a new variant by mutating the best performer."""
        variants = self._variants.get(name, [])
        if not variants:
            return None

        best = max(variants, key=lambda v: v.success_rate)

        # Simple evolution: add instruction refinements
        mutations = [
            "Be more concise in your response.",
            "Include a brief explanation of your reasoning.",
            "Prioritize correctness over speed.",
            "Consider edge cases in your approach.",
            "Structure your output for maximum clarity.",
        ]

        mutation = random.choice(mutations)
        new_prompt = f"{best.prompt_text}\n\nAdditional guidance: {mutation}"

        # Add as new variant
        new_variant = PromptVariant(
            name=name,
            variant_label=chr(65 + len(variants)),
            prompt_text=new_prompt,
        )
        self._variants[name].append(new_variant)
        return new_variant.id


# Singleton
prompt_optimizer = SelfImprovingPrompts()
