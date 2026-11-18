"""Demo-only human approval checkpoint.

The checkpoint models a pending, approved, or declined report review. It cannot
authorize a write, network call, tool call, or any other consequential action.
Approval is deliberately terminal for the demo: even an approved report has no
action endpoint to call.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field

from .security import SafetyError, assert_safe_display_text

ACTION_SCOPE = "demo_report_review"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class ApprovalError(RuntimeError):
    """Raised when an approval transition or action is not allowed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class ApprovalCheckpoint(BaseModel):
    """Serializable state for a report review, never an action authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    approval_id: str
    request_id: str
    action_scope: Literal["demo_report_review"] = ACTION_SCOPE
    status: ApprovalStatus
    consequential_action_permitted: Literal[False] = False
    decided_by: Literal["cli_assertion"] | None = None
    note: str | None = Field(default=None, max_length=500)


def approval_id_for(request_id: str) -> str:
    """Return a stable, non-secret approval reference for one request."""
    digest = hashlib.sha256(
        f"{request_id}:{ACTION_SCOPE}".encode("utf-8")
    ).hexdigest()[:16]
    return f"apr-{digest}"


class ApprovalGate:
    """Small state machine that cannot bypass the pending state."""

    def __init__(self, request_id: str) -> None:
        cleaned = request_id.strip()
        if not cleaned:
            raise ApprovalError(
                "invalid_request",
                "request_id must not be blank.",
            )
        self.request_id = cleaned
        self._status = ApprovalStatus.PENDING
        self._decided_by: Literal["cli_assertion"] | None = None
        self._note: str | None = None

    @property
    def approval_id(self) -> str:
        return approval_id_for(self.request_id)

    @property
    def status(self) -> ApprovalStatus:
        return self._status

    def checkpoint(self) -> ApprovalCheckpoint:
        return ApprovalCheckpoint(
            approval_id=self.approval_id,
            request_id=self.request_id,
            status=self._status,
            decided_by=self._decided_by,
            note=self._note,
        )

    def approve(
        self,
        *,
        approval_id: str,
        note: str | None = None,
    ) -> ApprovalCheckpoint:
        self._require_pending()
        self._require_matching_id(approval_id)
        cleaned_note = _clean_note(note)
        self._status = ApprovalStatus.APPROVED
        self._decided_by = "cli_assertion"
        self._note = cleaned_note
        return self.checkpoint()

    def decline(
        self,
        *,
        approval_id: str,
        note: str | None = None,
    ) -> ApprovalCheckpoint:
        self._require_pending()
        self._require_matching_id(approval_id)
        cleaned_note = _clean_note(note)
        self._status = ApprovalStatus.DECLINED
        self._decided_by = "cli_assertion"
        self._note = cleaned_note
        return self.checkpoint()

    def require_approved(self) -> None:
        """Allow only a review step to proceed; no action is exposed."""
        if self._status is not ApprovalStatus.APPROVED:
            raise ApprovalError(
                "approval_required",
                "The report must be explicitly approved before review continues.",
            )

    def require_pending(self) -> None:
        if self._status is not ApprovalStatus.PENDING:
            raise ApprovalError(
                "approval_already_decided",
                "This approval checkpoint has already been decided.",
            )

    def execute_consequential_action(self, action: str) -> NoReturn:
        """Fail closed for every action, including after approval."""
        raise ApprovalError(
            "consequential_action_disabled",
            f"The demo cannot perform {action!r}; approval is a review state "
            "only.",
        )

    def _require_pending(self) -> None:
        self.require_pending()

    def _require_matching_id(self, approval_id: str) -> None:
        if approval_id.strip() != self.approval_id:
            raise ApprovalError(
                "invalid_approval_id",
                "The supplied approval reference does not match this report.",
            )


def _clean_note(note: str | None) -> str | None:
    if note is None:
        return None
    if not isinstance(note, str):
        raise ApprovalError("invalid_note", "Approval note must be text.")
    cleaned = note.strip()
    if not cleaned:
        return None
    if len(cleaned) > 500:
        raise ApprovalError(
            "invalid_note",
            "Approval note must be 500 characters or fewer.",
        )
    try:
        assert_safe_display_text(cleaned, "approval_note")
    except SafetyError as exc:
        raise ApprovalError("invalid_note", exc.message) from exc
    return cleaned
