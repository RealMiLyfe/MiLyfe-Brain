"""
Prometheus metrics endpoint for MiLyfe Brain.

Exposes /metrics endpoint in Prometheus format for scraping.
Works alongside OpenTelemetry (OTEL exports to Prometheus via collector,
this provides direct scraping as an alternative).

Configuration:
    METRICS_ENABLED=true
    METRICS_PATH=/metrics
"""

import os
import time
from typing import Dict

from .logging_config import get_logger

logger = get_logger("metrics")

METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"


class PrometheusMetrics:
    """Simple Prometheus metrics collector (no external dependency)."""

    def __init__(self):
        self._counters: Dict[str, Dict] = {}
        self._gauges: Dict[str, Dict] = {}
        self._histograms: Dict[str, Dict] = {}
        self._start_time = time.time()

    def counter(self, name: str, help_text: str = "", labels: Dict[str, str] = None):
        """Increment a counter."""
        key = self._make_key(name, labels)
        if key not in self._counters:
            self._counters[key] = {"name": name, "help": help_text, "labels": labels or {}, "value": 0}
        self._counters[key]["value"] += 1

    def counter_add(self, name: str, value: float, help_text: str = "", labels: Dict[str, str] = None):
        """Add to a counter."""
        key = self._make_key(name, labels)
        if key not in self._counters:
            self._counters[key] = {"name": name, "help": help_text, "labels": labels or {}, "value": 0}
        self._counters[key]["value"] += value

    def gauge(self, name: str, value: float, help_text: str = "", labels: Dict[str, str] = None):
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = {"name": name, "help": help_text, "labels": labels or {}, "value": value}

    def histogram_observe(self, name: str, value: float, help_text: str = "", labels: Dict[str, str] = None):
        """Observe a value for histogram."""
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = {
                "name": name, "help": help_text, "labels": labels or {},
                "count": 0, "sum": 0, "buckets": {0.005: 0, 0.01: 0, 0.025: 0, 0.05: 0,
                                                    0.1: 0, 0.25: 0, 0.5: 0, 1: 0, 2.5: 0,
                                                    5: 0, 10: 0, float("inf"): 0}
            }
        h = self._histograms[key]
        h["count"] += 1
        h["sum"] += value
        for bucket in h["buckets"]:
            if value <= bucket:
                h["buckets"][bucket] += 1

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a unique key for metric + labels."""
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus output."""
        if not labels:
            return ""
        return "{" + ",".join(f'{k}="{v}"' for k, v in sorted(labels.items())) + "}"

    def generate_output(self) -> str:
        """Generate Prometheus text format output."""
        lines = []
        seen_helps = set()

        # Counters
        for key, data in self._counters.items():
            name = data["name"]
            if name not in seen_helps:
                lines.append(f"# HELP {name} {data['help']}")
                lines.append(f"# TYPE {name} counter")
                seen_helps.add(name)
            labels = self._format_labels(data["labels"])
            lines.append(f"{name}{labels} {data['value']}")

        # Gauges
        for key, data in self._gauges.items():
            name = data["name"]
            if name not in seen_helps:
                lines.append(f"# HELP {name} {data['help']}")
                lines.append(f"# TYPE {name} gauge")
                seen_helps.add(name)
            labels = self._format_labels(data["labels"])
            lines.append(f"{name}{labels} {data['value']}")

        # Histograms
        for key, data in self._histograms.items():
            name = data["name"]
            if name not in seen_helps:
                lines.append(f"# HELP {name} {data['help']}")
                lines.append(f"# TYPE {name} histogram")
                seen_helps.add(name)
            labels = self._format_labels(data["labels"])
            cumulative = 0
            for bucket, count in sorted(data["buckets"].items()):
                cumulative += count
                le = "+Inf" if bucket == float("inf") else str(bucket)
                bucket_labels = data["labels"].copy()
                bucket_labels["le"] = le
                lines.append(f"{name}_bucket{self._format_labels(bucket_labels)} {cumulative}")
            lines.append(f"{name}_count{labels} {data['count']}")
            lines.append(f"{name}_sum{labels} {data['sum']}")

        # Built-in metrics
        lines.append("# HELP milyfe_uptime_seconds Time since service start")
        lines.append("# TYPE milyfe_uptime_seconds gauge")
        lines.append(f"milyfe_uptime_seconds {time.time() - self._start_time:.2f}")

        return "\n".join(lines) + "\n"


# Singleton
prom_metrics = PrometheusMetrics()


def get_metrics_route():
    """Create a FastAPI route for /metrics."""
    from fastapi import APIRouter
    from fastapi.responses import PlainTextResponse

    router = APIRouter()

    @router.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        """Prometheus metrics endpoint."""
        return prom_metrics.generate_output()

    return router
