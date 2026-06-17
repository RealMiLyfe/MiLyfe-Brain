"""MiLyfe Brain — Compliance & Governance Layer.

Data lineage, license scanning, PII detection, retention policies.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import structlog

from config import settings

logger = structlog.get_logger()


class ComplianceService:
    """Compliance, governance, and data protection."""

    # PII patterns
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    # Known open-source licenses
    LICENSE_INDICATORS = {
        "MIT": ["mit license", "permission is hereby granted, free of charge"],
        "Apache-2.0": ["apache license", "version 2.0"],
        "GPL-3.0": ["gnu general public license", "version 3"],
        "BSD-3": ["redistribution and use in source and binary forms"],
        "ISC": ["isc license"],
    }

    async def scan_for_pii(self, content: str) -> List[Dict]:
        """Scan content for personally identifiable information."""
        findings = []
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                findings.append({
                    "type": pii_type,
                    "count": len(matches),
                    "samples": [m[:20] + "..." for m in matches[:3]],
                })
        return findings

    async def scan_file_for_pii(self, path: str) -> Dict:
        """Scan a workspace file for PII."""
        file_path = Path(settings.workspace_dir) / path
        if not file_path.exists():
            return {"error": "File not found"}

        content = file_path.read_text(errors="replace")
        findings = await self.scan_for_pii(content)

        return {
            "file": path,
            "pii_detected": len(findings) > 0,
            "findings": findings,
            "scanned_at": datetime.utcnow().isoformat(),
        }

    async def detect_license(self, content: str) -> Dict:
        """Detect license type in content."""
        content_lower = content.lower()
        for license_name, indicators in self.LICENSE_INDICATORS.items():
            if any(ind in content_lower for ind in indicators):
                return {"license": license_name, "confidence": "high"}

        if "license" in content_lower or "copyright" in content_lower:
            return {"license": "unknown", "confidence": "low"}

        return {"license": "none_detected", "confidence": "medium"}

    async def scan_workspace_licenses(self) -> List[Dict]:
        """Scan workspace for license files and indicators."""
        workspace = Path(settings.workspace_dir)
        results = []

        license_files = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]
        for lf in license_files:
            fp = workspace / lf
            if fp.exists():
                content = fp.read_text(errors="replace")
                detection = await self.detect_license(content)
                results.append({"file": lf, **detection})

        # Check package files
        for pkg_file in ["package.json", "pyproject.toml", "Cargo.toml"]:
            fp = workspace / pkg_file
            if fp.exists():
                content = fp.read_text(errors="replace")
                if "license" in content.lower():
                    results.append({"file": pkg_file, "has_license_field": True})

        return results

    async def get_data_lineage(self, output_file: str) -> Dict:
        """Track which inputs influenced a specific output."""
        # Query action logs to trace file operations
        from memory.database import ActionLogRow, async_session_factory
        from sqlalchemy import select

        async with async_session_factory() as session:
            # Find actions that wrote this file
            result = await session.execute(
                select(ActionLogRow)
                .where(ActionLogRow.description.contains(output_file))
                .order_by(ActionLogRow.timestamp.desc())
                .limit(20)
            )
            logs = result.scalars().all()

        lineage = []
        for log in logs:
            lineage.append({
                "action": log.action_type,
                "agent_role": log.agent_role,
                "description": log.description,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            })

        return {"file": output_file, "lineage": lineage}

    async def apply_retention_policy(self, max_age_days: int = 90):
        """Delete old memories/logs per retention policy."""
        from memory.database import ActionLogRow, AgentMemoryRow, async_session_factory
        from sqlalchemy import delete

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        async with async_session_factory() as session:
            # Delete old logs
            await session.execute(
                delete(ActionLogRow).where(ActionLogRow.timestamp < cutoff)
            )
            # Delete old memories
            await session.execute(
                delete(AgentMemoryRow).where(AgentMemoryRow.created_at < cutoff)
            )
            await session.commit()

        logger.info("retention_applied", max_age_days=max_age_days)


# Singleton
compliance_service = ComplianceService()
