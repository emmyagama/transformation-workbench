"""Deterministic guards for untrusted demo input.

The workbench has no shell, filesystem, or external-action tool. These guards
are still useful at the demo boundary: they reject path-like case selectors and
common instruction-injection text before any workflow step receives it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

CASE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
MAX_CASE_IDS = 20
_DISPLAY_CONTROL_PATTERN = re.compile(
    r"[\x00-\x1f\x7f\u2028\u2029\u202a-\u202e\u2066-\u2069]"
)


class SafetyError(ValueError):
    """A bounded, user-safe input rejection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SafetyFinding:
    code: str
    message: str


_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore|disregard|forget)\b[^.\n]{0,60}?"
            r"\b(?:previous|prior|above|system)\b[^.\n]{0,30}?"
            r"\b(?:instructions?|prompt|rules?)\b",
            re.IGNORECASE,
        ),
        "instruction-override text is not accepted as workflow input",
    ),
    (
        "system_prompt_exfiltration",
        re.compile(
            r"\b(?:reveal|show|print|dump|repeat)\b[^.\n]{0,40}?"
            r"\b(?:system prompt|hidden instructions|developer message)\b",
            re.IGNORECASE,
        ),
        "system-prompt exfiltration text is not accepted as workflow input",
    ),
    (
        "role_override",
        re.compile(
            r"\b(?:you are now|act as)\b[^.\n]{0,40}?"
            r"\b(?:admin|root|developer|system)\b",
            re.IGNORECASE,
        ),
        "role-override text is not accepted as workflow input",
    ),
    (
        "tool_action_request",
        re.compile(
            r"\b(?:call|invoke|execute|run)\b[^.\n]{0,30}?"
            r"\b(?:tool|command|shell|script|powershell|cmd)\b",
            re.IGNORECASE,
        ),
        "tool or command execution is not available to the workflow",
    ),
    (
        "path_traversal",
        re.compile(
            r"(?:\.\./|\.\.\\|/etc/passwd|[A-Za-z]:\\)",
            re.IGNORECASE,
        ),
        "path-like input is not accepted",
    ),
    (
        "shell_metacharacter",
        re.compile(
            r"(?:rm\s+-rf|\bcurl\b|\bwget\b|os\.system|subprocess\.)",
            re.IGNORECASE,
        ),
        "shell-like input is not accepted",
    ),
    (
        "credential_material",
        re.compile(
            r"\b(?:api[_ -]?key|access[_ -]?token|password|secret)\b"
            r"\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        "credential-like material is not accepted as workflow input",
    ),
)


def validate_case_id(value: str) -> str:
    """Return a normalized case ID or reject a path-like selector."""
    cleaned = value.strip()
    if not cleaned:
        raise SafetyError("invalid_case_id", "Case IDs must not be blank.")
    if ".." in cleaned or not CASE_ID_PATTERN.fullmatch(cleaned):
        raise SafetyError(
            "invalid_case_id",
            "Case IDs must be short identifiers such as C-009; paths are not "
            "accepted.",
        )
    return cleaned


def validate_case_ids(values: Iterable[str]) -> list[str]:
    """Normalize, de-duplicate, and bound a requested case set."""
    normalized: list[str] = []
    for value in values:
        cleaned = validate_case_id(str(value))
        if cleaned not in normalized:
            normalized.append(cleaned)
    if len(normalized) > MAX_CASE_IDS:
        raise SafetyError(
            "invalid_case_ids",
            f"At most {MAX_CASE_IDS} case IDs are supported.",
        )
    return normalized


def scan_untrusted_text(text: str) -> list[SafetyFinding]:
    """Return deterministic findings for common injection and path patterns."""
    findings: list[SafetyFinding] = []
    for code, pattern, message in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            findings.append(SafetyFinding(code=code, message=message))
    return findings


def assert_safe_untrusted_text(text: str, field: str) -> None:
    """Reject the first unsafe pattern in an untrusted text field."""
    findings = scan_untrusted_text(text)
    if findings:
        finding = findings[0]
        raise SafetyError(
            finding.code,
            f"{field}: {finding.message}.",
        )


def assert_safe_display_text(text: str, field: str) -> None:
    """Reject untrusted text that could break a single rendered report line."""
    assert_safe_untrusted_text(text, field)
    if _DISPLAY_CONTROL_PATTERN.search(text):
        raise SafetyError(
            "unsafe_display_text",
            f"{field}: line breaks and control characters are not accepted.",
        )


def assert_safe_optional_text(text: str | None, field: str) -> None:
    if text:
        assert_safe_untrusted_text(text, field)
