"""Command Safety Classifier — 3-tier risk classification.

Allowlist → Pattern matching → Injection detection.
Risk levels: safe, caution, dangerous, blocked.
"""

import re

# Allowlisted commands (always safe)
ALLOWLIST = {
    "ls", "pwd", "echo", "cat", "head", "tail", "wc", "sort", "uniq",
    "grep", "find", "which", "whoami", "date", "uname", "df", "du",
    "python", "python3", "pip", "pip3", "node", "npm", "npx", "yarn",
    "git status", "git log", "git diff", "git branch", "git show",
    "cargo", "go", "rustc", "javac", "java", "gcc", "g++", "make",
}

# Dangerous patterns
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",           # rm -rf /
    r"rm\s+-rf\s+~",           # rm -rf ~
    r"mkfs\.",                  # filesystem format
    r"dd\s+if=",               # disk destroyer
    r":\(\)\{.*\}",            # fork bomb
    r"chmod\s+777\s+/",        # dangerous chmod
    r"chown\s+.*\s+/",         # dangerous chown
    r"shutdown",               # system shutdown
    r"reboot",                 # system reboot
    r"init\s+[06]",            # init level change
    r"systemctl\s+(stop|disable)\s+(ssh|sshd|network|firewall)",
]

# Injection patterns
INJECTION_PATTERNS = [
    r"\$\(.*\)",               # Command substitution
    r"`.*`",                   # Backtick execution
    r"\|\s*bash",              # Piping to shell
    r"\|\s*sh",                # Piping to shell
    r";\s*rm\s",               # Chained deletion
    r"&&\s*rm\s",              # Chained deletion
    r"eval\s",                 # eval execution
    r"exec\s",                 # exec
    r"source\s+/dev/",         # Source device
    r">\s*/etc/",              # Write to /etc
    r">\s*/dev/",              # Write to device
]

# Caution patterns (allowed but logged)
CAUTION_PATTERNS = [
    r"rm\s",                   # Any rm command
    r"chmod\s",                # Permission changes
    r"chown\s",                # Ownership changes
    r"kill\s",                 # Process killing
    r"pkill\s",                # Process killing
    r"wget\s",                 # Download
    r"curl\s.*-o",             # Download
    r"pip\s+install",          # Package install
    r"npm\s+install",          # Package install
    r"apt\s+install",          # Package install
    r"docker\s",               # Docker commands
    r"sudo\s",                 # Sudo
]


def classify_command(command: str) -> str:
    """Classify a shell command's risk level.

    Returns: safe, caution, dangerous, blocked
    """
    command_stripped = command.strip().lower()

    # Check allowlist first (fast path)
    first_word = command_stripped.split()[0] if command_stripped else ""
    if first_word in ALLOWLIST or command_stripped in ALLOWLIST:
        return "safe"

    # Check for blocked/dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return "blocked"

    # Check for injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, command):
            return "dangerous"

    # Check for caution patterns
    for pattern in CAUTION_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return "caution"

    return "safe"
