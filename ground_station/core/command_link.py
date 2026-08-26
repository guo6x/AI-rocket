"""Plaintext command acknowledgement and timeout state for both transports."""

from __future__ import annotations

from dataclasses import dataclass
import re
import time


ACK_RE = re.compile(r"^ACK ([a-z_]+)$")
NACK_RE = re.compile(
    r"^NACK (malformed|invalid_state|out_of_range|estop_latched|"
    r"unknown_command|overlong) ([a-z_]+)$"
)


def command_name(command: str) -> str:
    return command.strip().split(":", 1)[0]


@dataclass(frozen=True)
class CommandUpdate:
    status: str
    command: str
    detail: str = ""


def parse_command_response(line: str) -> CommandUpdate | None:
    text = line.strip()
    match = ACK_RE.fullmatch(text)
    if match:
        return CommandUpdate("ACKNOWLEDGED", match.group(1))
    match = NACK_RE.fullmatch(text)
    if match:
        return CommandUpdate("NACK", match.group(2), match.group(1))
    return None


class CommandTracker:
    """Track one unambiguous in-flight plaintext command."""

    def __init__(self, timeout_seconds: float = 1.5):
        self.timeout_seconds = timeout_seconds
        self.pending_command: str | None = None
        self.pending_name: str | None = None
        self.deadline: float | None = None

    @property
    def pending(self) -> bool:
        return self.pending_command is not None

    def mark_sent(self, command: str, now: float | None = None) -> CommandUpdate:
        if self.pending:
            raise RuntimeError("a command acknowledgement is already pending")
        now = time.monotonic() if now is None else now
        self.pending_command = command.strip()
        self.pending_name = command_name(command)
        self.deadline = now + self.timeout_seconds
        return CommandUpdate("SENT", self.pending_command)

    def resolve(self, line: str) -> CommandUpdate | None:
        response = parse_command_response(line)
        if response is None or not self.pending:
            return None
        if response.command not in (self.pending_name, "unknown"):
            return None
        command = self.pending_command or response.command
        self.clear()
        return CommandUpdate(response.status, command, response.detail)

    def expire(self, now: float | None = None) -> CommandUpdate | None:
        if not self.pending or self.deadline is None:
            return None
        now = time.monotonic() if now is None else now
        if now < self.deadline:
            return None
        command = self.pending_command or "unknown"
        self.clear()
        return CommandUpdate("TIMEOUT", command, "no ACK/NACK received")

    def fail(self, command: str, detail: str) -> CommandUpdate:
        self.clear()
        return CommandUpdate("FAILED", command.strip(), detail)

    def reject_local(self, command: str, detail: str) -> CommandUpdate:
        return CommandUpdate("FAILED", command.strip(), detail)

    def cancel_pending(self, detail: str) -> CommandUpdate | None:
        if not self.pending:
            return None
        command = self.pending_command or "unknown"
        self.clear()
        return CommandUpdate("FAILED", command, detail)

    def clear(self) -> None:
        self.pending_command = None
        self.pending_name = None
        self.deadline = None
