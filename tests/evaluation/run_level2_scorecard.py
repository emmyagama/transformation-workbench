"""Run every frozen Level 2 case and write a per-case scorecard.

This runner covers the full workflow entrypoint, the A2A coordinator entrypoint,
and the direct baseline for the shared comparison cases. It uses only local
deterministic components and the fixed synthetic fixture.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from transformation_workbench.a2a.phase2_coordinator import CoordinatorError
from transformation_workbench.approval import ApprovalError, ApprovalGate, approval_id_for
from transformation_workbench.intake import IntakeRequest
from transformation_workbench.workflow import run_workflow

from tests.evaluation.run_level2_comparison import (
    SHARED_CASES,
    _load_corpus,
    _load_manifest,
    _run_a2a,
    _run_baseline,
    _summarize_path,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "docs" / "evidence" / "level-2"

WORKFLOW_VARIANTS = {"L2-01a", "L2-05b", "L2-07a", "L2-07b", "L2-07c"}

COORDINATOR_KINDS = {
    "L2-08a": "duplicate_replay",
    "L2-08b": "duplicate_conflict",
    "L2-08c": "unavailable_specialist",
    "L2-09a": "slow_specialist",
    "L2-09b": "slow_specialist",
    "L2-10a": "malformed_json",
    "L2-10b": "wrong_mime",
}


@dataclass(frozen=True)
class WorkflowOutcome:
    status: str
    error_code: str | None
    cause_code: str | None
    report: Any | None


def _default_outcome() -> str:
    return (
        "Review the synthetic service-request intake and decide which evidence "
        "to inspect next."
    )


def _cause_from_validation(exc: ValidationError) -> str | None:
    message = str(exc)
    if "instruction-override" in message:
        return "instruction_override"
    if "system-prompt" in message:
        return "system_prompt_exfiltration"
    if "role-override" in message:
        return "role_override"
    if "tool or command execution" in message:
        return "tool_action_request"
    if "path-like input" in message:
        return "path_traversal"
    return None


async def _run_workflow_variant(variant: dict[str, Any]) -> WorkflowOutcome:
    input_data = variant.get("input", {})
    request_id = input_data.get("request_id", f"level2-{variant['variant_id'].lower()}")
    desired_outcome = input_data.get("desired_outcome", _default_outcome())
    case_ids = input_data.get("case_ids", ["C-009", "C-006", "C-014"])
    decision = input_data.get("decision", "pending")
    approval_id = input_data.get("approval_id")
    if approval_id == "derived-from-request-id":
        approval_id = approval_id_for(request_id)
    timeout = float(input_data.get("timeout_seconds", 20.0))
    max_retries = int(input_data.get("max_retries", 1))

    try:
        intake = IntakeRequest(
            request_id=request_id,
            desired_outcome=desired_outcome,
            case_ids=case_ids,
        )
        report = await run_workflow(
            intake,
            decision=decision,
            approval_id=approval_id,
            timeout=timeout,
            max_retries=max_retries,
        )
        return WorkflowOutcome("complete", None, None, report)
    except ValidationError as exc:
        return WorkflowOutcome(
            "refused",
            "invalid_intake",
            _cause_from_validation(exc),
            None,
        )
    except ApprovalError as exc:
        status = "refused" if exc.code in {"approval_id_required"} else "failure"
        return WorkflowOutcome(status, exc.code, None, None)
    except CoordinatorError as exc:
        return WorkflowOutcome("failure", exc.code, None, None)


def _workflow_dimensions(
    variant: dict[str, Any],
    outcome: WorkflowOutcome,
    manifest: dict[str, Any],
) -> dict[str, bool]:
    expected = variant["expected"]
    if expected["status"] != "complete":
        expected_codes = {
            code
            for code in (expected.get("error_code"), expected.get("cause_code"))
            if code
        }
        observed_codes = {
            code
            for code in (outcome.error_code, outcome.cause_code)
            if code
        }
        return {
            "status_matches": outcome.status == expected["status"],
            "expected_error_code_seen": bool(expected_codes & observed_codes),
            "no_successful_result": outcome.report is None,
            "bounded_terminal_status": outcome.status in {"refused", "failure"},
        }

    report = outcome.report
    if report is None:
        return {
            "status_matches": False,
            "report_present": False,
        }
    expected_baseline = manifest["baseline"]
    metrics = {item.name: item.value for item in report.metrics}
    exceptions = sorted(
        (item.case_id, item.row_number, item.reason)
        for item in report.exceptions
    )
    expected_exceptions = sorted(
        (item["case_id"], item["row_number"], item["reason"])
        for item in expected_baseline["exceptions"]
    )
    requested_ids = variant.get("input", {}).get(
        "case_ids", ["C-009", "C-006", "C-014"]
    )
    cases_ok = {
        item.case_id for item in report.case_observations
    } == set(requested_ids)
    for case_id in requested_ids:
        values = expected_baseline["requested_cases"][case_id]
        observed = next(
            (item for item in report.case_observations if item.case_id == case_id),
            None,
        )
        if observed is None:
            cases_ok = False
            continue
        for field, value in values.items():
            if getattr(observed, field) != value:
                cases_ok = False
    expected_approval = "approved" if variant["variant_id"] == "L2-07c" else "pending"
    trace = report.protocol_trace
    discoveries = [event for event in trace if event.step == "discover_card"]
    sends = [event for event in trace if event.step == "send_task"]
    trace_ok = (
        len(discoveries) == 2
        and len(sends) == 2
        and all(
            event.state == "TASK_STATE_COMPLETED"
            and event.task_id
            and event.context_id
            for event in sends
        )
    )
    action_method_raises = True
    if variant["variant_id"] == "L2-07c":
        gate = ApprovalGate(report.request_id)
        gate.approve(approval_id=report.approval.approval_id)
        try:
            gate.execute_consequential_action("create ticket")
            action_method_raises = False
        except ApprovalError as exc:
            action_method_raises = exc.code == "consequential_action_disabled"
    return {
        "status_matches": outcome.status == "complete",
        "report_present": True,
        "required_fields_present": all(
            field in report.model_dump(mode="json")
            for field in manifest["required_report_fields"]
        ),
        "required_sections_present": all(
            section in report.rendered_markdown
            for section in manifest["required_report_sections"]
        ),
        "metrics_exact_match": metrics == expected_baseline["metrics"],
        "exceptions_exact_match": exceptions == expected_exceptions,
        "requested_cases_exact_match": cases_ok,
        "options_exact_match": [
            item.option_id for item in report.automation_opportunities
        ]
        == [item["option_id"] for item in expected_baseline["options"]],
        "approval_matches": report.approval.status.value == expected_approval,
        "consequential_action_permitted_false": (
            report.approval.consequential_action_permitted is False
        ),
        "report_states_no_action": (
            "No external network, write, or business action"
            in report.rendered_markdown
        ),
        "trace_complete": trace_ok,
        "read_only_trace": all(
            event.method in {"GET", "POST", "NONE"} for event in trace
        ),
        "action_method_raises": action_method_raises,
    }


async def _run_coordinator_variant(
    variant: dict[str, Any],
) -> tuple[Any, dict[str, Any] | None]:
    variant_id = variant["variant_id"]
    shared = dict(SHARED_CASES)
    kind = shared.get(variant_id) or COORDINATOR_KINDS[variant_id]
    input_data = variant.get("input", {})
    request_id = input_data.get("request_id", f"level2-{variant_id.lower()}")
    case_ids = input_data.get("case_ids", ["C-009", "C-006", "C-014"])
    a2a = await _run_a2a(variant_id, kind, request_id, case_ids)
    baseline_summary = None
    if variant_id in shared:
        baseline = await _run_baseline(kind, request_id, case_ids)
        baseline_summary = _summarize_path(
            variant,
            baseline.status,
            baseline.error_code,
            None,
            baseline.evidence_pack,
            baseline.solution_options,
            _load_manifest(),
        )
    return a2a, baseline_summary


def _score_coordinator(
    variant: dict[str, Any],
    a2a: Any,
    baseline_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest = _load_manifest()
    summary = _summarize_path(
        variant,
        a2a.status,
        a2a.error_code,
        a2a.cause_code,
        a2a.result.measured_facts if a2a.result else None,
        a2a.result.solution_options if a2a.result else None,
        manifest,
    )
    if variant["variant_id"] == "L2-08a":
        trace = a2a.result.trace if a2a.result else []
        summary["dimensions"]["duplicate_replay_trace"] = (
            bool(trace)
            and trace[-1].step == "duplicate_replay"
            and sum(1 for event in trace if event.step == "send_task") == 2
        )
        summary["passed"] = all(summary["dimensions"].values())
    return {
        "status": a2a.status,
        "error_code": a2a.error_code,
        "cause_code": a2a.cause_code,
        "dimensions": summary["dimensions"],
        "passed": summary["passed"],
        "baseline": baseline_summary,
    }


async def main() -> None:
    corpus = _load_corpus()
    rows: list[dict[str, Any]] = []
    for case in corpus["cases"]:
        for variant in case["variants"]:
            variant_id = variant["variant_id"]
            entrypoint = case["entrypoint"]
            if variant_id in WORKFLOW_VARIANTS:
                outcome = await _run_workflow_variant(variant)
                dimensions = _workflow_dimensions(
                    variant, outcome, _load_manifest()
                )
                row = {
                    "case_id": case["case_id"],
                    "family": case["family"],
                    "variant_id": variant_id,
                    "entrypoint": entrypoint,
                    "status": outcome.status,
                    "error_code": outcome.error_code,
                    "cause_code": outcome.cause_code,
                    "dimensions": dimensions,
                    "passed": all(dimensions.values()),
                    "baseline": None,
                }
            else:
                a2a, baseline_summary = await _run_coordinator_variant(variant)
                scored = _score_coordinator(variant, a2a, baseline_summary)
                row = {
                    "case_id": case["case_id"],
                    "family": case["family"],
                    "variant_id": variant_id,
                    "entrypoint": entrypoint,
                    "status": scored["status"],
                    "error_code": scored["error_code"],
                    "cause_code": scored["cause_code"],
                    "dimensions": scored["dimensions"],
                    "passed": scored["passed"],
                    "baseline": scored["baseline"],
                }
            rows.append(row)

    misses = [row for row in rows if not row["passed"]]
    report = {
        "pack_id": corpus["pack_id"],
        "pack_version": corpus["pack_version"],
        "scorecard_version": "1.0.0",
        "baseline_commit": corpus["baseline_commit"],
        "variant_count": len(rows),
        "passed": len(rows) - len(misses),
        "missed": len(misses),
        "rows": rows,
        "notes": [
            "The scorecard covers all frozen corpus variants, not only the shared baseline comparison.",
            "Workflow variants are exercised through the full intake-to-approval workflow.",
            "Coordinator variants are exercised through the real local A2A coordinator and specialists.",
            "The direct baseline is compared only where it is applicable; other variants are A2A-specific or workflow/approval-specific.",
            "No hosted model, provider, external system, credential, or real data is used.",
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "scorecard-v1.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Level 2 per-case scorecard v1",
        "",
        f"**Pack:** `{report['pack_id']}` v{report['pack_version']}",
        f"**Baseline commit:** `{report['baseline_commit']}`",
        "",
        "## Summary",
        "",
        f"- Variants: **{report['variant_count']}**",
        f"- Passed: **{report['passed']}**",
        f"- Missed: **{report['missed']}**",
        "",
        "## Per-case results",
        "",
        "| Case | Variant | Entrypoint | Status | Code / cause | Pass | Failed dimensions |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        failed = [
            name for name, value in row["dimensions"].items() if not value
        ]
        code = row["error_code"] or "-"
        cause = row["cause_code"] or "-"
        lines.append(
            f"| {row['case_id']} | {row['variant_id']} | {row['entrypoint']} | "
            f"{row['status']} | {code} / {cause} | {row['passed']} | "
            f"{', '.join(failed) if failed else '-'} |"
        )
    lines.extend(
        [
            "",
            "## Misses",
            "",
        ]
    )
    if misses:
        for row in misses:
            failed = [
                name for name, value in row["dimensions"].items() if not value
            ]
            lines.append(
                f"- **{row['variant_id']}:** {', '.join(failed)}"
            )
    else:
        lines.append("No misses in the frozen local corpus.")
    lines.extend(
        [
            "",
            "## Notes",
            "",
        ]
    )
    for note in report["notes"]:
        lines.append(f"- {note}")
    (OUTPUT_DIR / "scorecard-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variant_count": report["variant_count"],
                "passed": report["passed"],
                "missed": report["missed"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
