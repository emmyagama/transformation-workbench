"""End-to-end synthetic Transformation Workbench workflow."""

from __future__ import annotations

from typing import Literal

from .a2a.local_runtime import run_local_diagnosis
from .approval import ApprovalError, ApprovalGate
from .intake import IntakeRequest
from .report import TransformationReport, build_report

Decision = Literal["pending", "approved", "declined"]


async def run_workflow(
    intake: IntakeRequest,
    *,
    decision: Decision = "pending",
    approval_id: str | None = None,
    approval_note: str | None = None,
    timeout: float = 20.0,
    max_retries: int = 1,
) -> TransformationReport:
    """Run the full read-only workflow and stop at an approval checkpoint.

    The report is produced in every case. No decision enables a write, network
    call, tool action, or business action.
    """
    result = await run_local_diagnosis(
        intake.request_id,
        intake.case_ids,
        timeout=timeout,
        max_retries=max_retries,
    )
    gate = ApprovalGate(intake.request_id)
    _apply_decision(
        gate,
        decision=decision,
        approval_id=approval_id,
        approval_note=approval_note,
    )
    return build_report(intake, result, gate)


def _apply_decision(
    gate: ApprovalGate,
    *,
    decision: Decision,
    approval_id: str | None,
    approval_note: str | None,
) -> None:
    if decision == "pending":
        if approval_id is not None:
            raise ApprovalError(
                "unexpected_approval_id",
                "An approval reference is only accepted with an approved or "
                "declined decision.",
            )
        if approval_note is not None:
            raise ApprovalError(
                "unexpected_approval_note",
                "An approval note is only accepted with an approved or "
                "declined decision.",
            )
        gate.require_pending()
        return
    if approval_id is None:
        raise ApprovalError(
            "approval_id_required",
            "An explicit approval reference is required for a decision.",
        )
    if decision == "approved":
        gate.approve(approval_id=approval_id, note=approval_note)
        return
    if decision == "declined":
        gate.decline(approval_id=approval_id, note=approval_note)
        return
    raise ApprovalError(
        "invalid_decision",
        "Decision must be pending, approved, or declined.",
    )
