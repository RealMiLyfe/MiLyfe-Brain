"""MiLyfe Brain — Command Safety Classifier.

3-tier: allowlist → pattern matching → injection detection.
"""

from __future__ import annotations

import re

# Allowlisted safe commands (fast pass)
SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "echo", "pwd", "whoami",
    "date", "wc", "sort", "uniq", "grep", "find", "tree",
    "python", "python3", "pip", "pip3", "node", "npm", "npx",
    "git", "make", "cargo", "go", "java", "javac",
    "mkdir", "touch", "cp", "mv", "ln",
    "curl", "wget",
    "docker", "docker-compose",
    "pytest", "ruff", "mypy", "eslint",
}

# Blocked patterns (never allow)
BLOCKED_PATTERNS = [
    r"rm\s+(-rf?|--recursive)\s+/(?!workspace)",  # rm -rf outside workspace
    r":(){ :\|:& };:",  # Fork bomb
    r"dd\s+if=.*of=/dev/",  # Destructive dd
    r"mkfs\.",  # Format disk
    r"chmod\s+777\s+/",  # Dangerous permissions on root
    r">\s*/etc/",  # Overwrite system files
    r"wget.*\|\s*sh",  # Download and execute
    r"curl.*\|\s*(sh|bash)",  # Download and execute
    r"\$\(.*\)",  # Command substitution (potential injection)
    r"`[^`]+`",  # Backtick execution
    r";\s*(rm|shutdown|reboot|halt|poweroff)",  # Chained dangerous commands
    r"&&\s*(rm|shutdown|reboot|halt|poweroff)",
    r"sudo\s+rm\s+-rf\s+/",  # The classic
    r"shutdown|reboot|halt|poweroff",  # System control
    r"/dev/(sd|nvme|vd)",  # Direct disk access
]

# Caution patterns (allow but warn)
CAUTION_PATTERNS = [
    r"rm\s+",  # Any rm command
    r"pip\s+install",  # Installing packages
    r"npm\s+install",  # Installing packages
    r"chmod",  # Permission changes
    r"chown",  # Ownership changes
    r"kill",  # Process management
    r"pkill",  # Process management
    r"git\s+(push|reset|clean)",  # Destructive git
    r"docker\s+(rm|rmi|prune)",  # Docker cleanup
]


def classify_command(command: str) -> str:
    """Classify a shell command's risk level.

    Returns: "safe", "caution", "dangerous", or "blocked"
    """
    command = command.strip()

    if not command:
        return "safe"

    # Check blocked patterns first
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return "blocked"

    # Check injection indicators
    if _has_injection(command):
        return "dangerous"

    # Check allowlist (first word)
    first_word = command.split()[0].split("/")[-1] if command.split() else ""
    if first_word in SAFE_COMMANDS:
        # Even safe commands can be dangerous with certain args
        for pattern in CAUTION_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return "caution"
        return "safe"

    # Check caution patterns
    for pattern in CAUTION_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return "caution"

    # Unknown commands default to caution
    return "caution"


def _has_injection(command: str) -> bool:
    """Detect command injection attempts."""
    indicators = [
        "$(", "`",  # Command substitution
        "| sh", "| bash", "| zsh",  # Piping to shell
        "${IFS}",  # IFS bypass
        "\\x", "\\u",  # Encoded characters
        "eval ", "exec ",  # Dynamic execution
    ]
    for indicator in indicators:
        if indicator in command:
            return True
    return False
