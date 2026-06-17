"""MiLyfe Brain — Shell Command Risk Classifier.

Classifies shell commands into risk levels based on pattern matching.
Detects dangerous commands, injection attempts, and safe operations.
"""

from __future__ import annotations

import re
from typing import Dict, List


# Risk level constants
RISK_SAFE = "safe"
RISK_CAUTION = "caution"
RISK_DANGEROUS = "dangerous"
RISK_BLOCKED = "blocked"

# Commands that are always safe
_SAFE_COMMANDS = frozenset({
    "ls", "cat", "pwd", "echo", "head", "tail", "wc", "whoami",
    "date", "cal", "df", "du", "file", "which", "whereis",
    "hostname", "uname", "uptime", "env", "printenv", "id",
    "basename", "dirname", "realpath", "readlink", "stat",
    "true", "false", "test",
})

# Dangerous command patterns (regex)
_DANGEROUS_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive\s+--force|-[a-zA-Z]*f[a-zA-Z]*r)"), "Recursive forced deletion (rm -rf)"),
    (re.compile(r"\brm\s+-rf\s+/"), "Recursive forced deletion of root path"),
    (re.compile(r"\bdd\b"), "Direct disk write (dd)"),
    (re.compile(r"\bmkfs\b"), "Filesystem formatting (mkfs)"),
    (re.compile(r"\bformat\b"), "Disk formatting"),
    (re.compile(r":\(\)\s*\{\s*:\|\s*:\s*&\s*\}"), "Fork bomb"),
    (re.compile(r">\s*/dev/sd[a-z]"), "Direct write to block device"),
    (re.compile(r"\bshutdown\b"), "System shutdown"),
    (re.compile(r"\breboot\b"), "System reboot"),
    (re.compile(r"\binit\s+0"), "System halt"),
    (re.compile(r"\bkill\s+-9\s+1\b"), "Kill init process"),
    (re.compile(r"\bchmod\s+777\s+/"), "Unsafe root permission change"),
    (re.compile(r"\bchown\s+.*\s+/"), "Root ownership change"),
]

# Blocked patterns (never allow)
_BLOCKED_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\s+-rf\s+/\s*$"), "Deletion of entire filesystem"),
    (re.compile(r"\brm\s+-rf\s+/\*"), "Deletion of all root contents"),
    (re.compile(r">\s*/dev/sda"), "Overwrite primary disk"),
    (re.compile(r"\bmkfs\s+/dev/sd"), "Format primary disk"),
    (re.compile(r":\(\)\s*\{\s*:\|\s*:"), "Fork bomb"),
]

# Injection detection patterns
_INJECTION_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"`[^`]+`"), "Backtick command substitution"),
    (re.compile(r"\$\([^)]+\)"), "Dollar-paren command substitution"),
    (re.compile(r"\|\s*(bash|sh|zsh|dash|ksh)"), "Pipe to shell interpreter"),
    (re.compile(r";\s*(bash|sh|zsh)\s+-c"), "Chained shell execution"),
    (re.compile(r"eval\s+"), "Eval statement"),
    (re.compile(r"\bsource\s+/dev/"), "Source from device"),
    (re.compile(r"curl\s+.*\|\s*(bash|sh)"), "Download and execute"),
    (re.compile(r"wget\s+.*\|\s*(bash|sh)"), "Download and execute"),
]

# Caution-level patterns
_CAUTION_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\b"), "File deletion (rm)"),
    (re.compile(r"\bmv\b"), "File move/rename (mv)"),
    (re.compile(r"\bchmod\b"), "Permission change (chmod)"),
    (re.compile(r"\bchown\b"), "Ownership change (chown)"),
    (re.compile(r"\bsudo\b"), "Elevated privileges (sudo)"),
    (re.compile(r"\bpip\s+install\b"), "Package installation (pip)"),
    (re.compile(r"\bnpm\s+install\b"), "Package installation (npm)"),
    (re.compile(r"\bapt\s+(install|remove)\b"), "System package operation (apt)"),
    (re.compile(r"\bcurl\b"), "Network request (curl)"),
    (re.compile(r"\bwget\b"), "Network request (wget)"),
    (re.compile(r"\bgit\s+push\b"), "Git push"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "Git hard reset"),
    (re.compile(r"\bkill\b"), "Process termination (kill)"),
    (re.compile(r"\bpkill\b"), "Process termination (pkill)"),
]


def classify_command(command: str) -> Dict[str, object]:
    """Classify a shell command by its risk level.

    Analyzes the command against known patterns to determine
    safety. Returns a dict with the risk level and reasons.

    Args:
        command: The shell command string to classify.

    Returns:
        Dict with keys:
            - risk_level: "safe" | "caution" | "dangerous" | "blocked"
            - reasons: List of string explanations for the classification.
    """
    if not command or not command.strip():
        return {"risk_level": RISK_SAFE, "reasons": ["Empty command"]}

    command = command.strip()
    reasons: List[str] = []

    # Check blocked patterns first (highest priority)
    for pattern, reason in _BLOCKED_PATTERNS:
        if pattern.search(command):
            reasons.append(reason)
    if reasons:
        return {"risk_level": RISK_BLOCKED, "reasons": reasons}

    # Check injection patterns
    for pattern, reason in _INJECTION_PATTERNS:
        if pattern.search(command):
            reasons.append(f"Injection detected: {reason}")
    if reasons:
        return {"risk_level": RISK_DANGEROUS, "reasons": reasons}

    # Check dangerous patterns
    for pattern, reason in _DANGEROUS_PATTERNS:
        if pattern.search(command):
            reasons.append(reason)
    if reasons:
        return {"risk_level": RISK_DANGEROUS, "reasons": reasons}

    # Check if the base command is in the safe list
    base_command = _extract_base_command(command)
    if base_command in _SAFE_COMMANDS:
        return {"risk_level": RISK_SAFE, "reasons": [f"Allowlisted command: {base_command}"]}

    # Check caution patterns
    for pattern, reason in _CAUTION_PATTERNS:
        if pattern.search(command):
            reasons.append(reason)
    if reasons:
        return {"risk_level": RISK_CAUTION, "reasons": reasons}

    # Default: caution for unknown commands
    return {"risk_level": RISK_CAUTION, "reasons": [f"Unknown command: {base_command}"]}


def _extract_base_command(command: str) -> str:
    """Extract the base command name from a full command string.

    Handles pipes, redirects, and environment variable prefixes.

    Args:
        command: Full shell command string.

    Returns:
        The base command name (first word, ignoring env vars).
    """
    # Remove leading env var assignments (e.g., "FOO=bar command")
    parts = command.split()
    for part in parts:
        if "=" not in part or part.startswith("-"):
            return part.split("/")[-1]  # Handle full paths
    return parts[0] if parts else ""
