"""CLI for the read-only end-to-end Transformation Workbench demo."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from .a2a.claims import UnsupportedClaimError
from .a2a.phase2_coordinator import CoordinatorError
from .a2a.summary import SummaryError
from .approval import ApprovalError
from .intake import DEFAULT_CASE_IDS, IntakeRequest
from .report import ReportError
from .security import SafetyError
from .workflow import run_workflow


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the synthetic intake-to-approval Transformation Workbench "
            "workflow. The workflow is read-only and performs no business action."
        ),
    )
    parser.add_argument(
        "--request-id",
        required=True,
        help="Non-empty correlation ID for this synthetic run.",
    )
    parser.add_argument(
        "--desired-outcome",
        required=True,
        help="Requested outcome for the synthetic process.",
    )
    parser.add_argument(
        "--process-name",
        default="Synthetic email service-request intake",
        help="Synthetic process label.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=None,
        dest="case_ids",
        help=(
            "Synthetic case ID to inspect; repeat for multiple IDs. "
            "Defaults to C-009, C-006, and C-014."
        ),
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional synthetic notes; do not include real or sensitive data.",
    )
    parser.add_argument(
        "--decision",
        choices=("pending", "approved", "declined"),
        default="pending",
        help="Demo review decision. The default pauses at pending.",
    )
    parser.add_argument(
        "--approval-id",
        default=None,
        help="Approval reference printed by a pending run; required for a decision.",
    )
    parser.add_argument(
        "--approval-note",
        default=None,
        help="Optional reviewer note for an approved or declined decision.",
    )
    parser.add_argument(
        "--timeout",
        type=_timeout_seconds,
        default=20.0,
        help="Per-operation A2A timeout in seconds (1-120).",
    )
    parser.add_argument(
        "--max-retries",
        type=_retry_count,
        default=1,
        help="Bounded transient retry count (0-5).",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Print the decision brief or the structured report.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Keep protocol and server logs on stderr.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    _configure_logging(verbose=args.verbose)
    try:
        intake = IntakeRequest(
            request_id=args.request_id,
            process_name=args.process_name,
            desired_outcome=args.desired_outcome,
            case_ids=(
                list(DEFAULT_CASE_IDS)
                if args.case_ids is None
                else args.case_ids
            ),
            notes=args.notes,
        )
        report = asyncio.run(
            run_workflow(
                intake,
                decision=args.decision,
                approval_id=args.approval_id,
                approval_note=args.approval_note,
                timeout=args.timeout,
                max_retries=args.max_retries,
            )
        )
    except ValidationError as exc:
        _fail("invalid_intake", _validation_message(exc))
        return
    except (
        CoordinatorError,
        SummaryError,
        UnsupportedClaimError,
        SafetyError,
        ApprovalError,
        ReportError,
    ) as exc:
        _fail(
            getattr(exc, "code", "unsupported_claim"),
            getattr(exc, "message", str(exc)),
        )
        return

    if args.format == "json":
        print(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        print(report.rendered_markdown, end="")


def _timeout_seconds(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number") from exc
    if not 0 < parsed <= 120:
        raise argparse.ArgumentTypeError("timeout must be between 1 and 120")
    return parsed


def _retry_count(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("max-retries must be an integer") from exc
    if not 0 <= parsed <= 5:
        raise argparse.ArgumentTypeError("max-retries must be between 0 and 5")
    return parsed


def _configure_logging(*, verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        if getattr(existing, "_transformation_workbench_cli", False):
            root.removeHandler(existing)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    setattr(handler, "_transformation_workbench_cli", True)
    root.addHandler(handler)
    for name in ("httpx", "httpcore", "a2a"):
        logging.getLogger(name).setLevel(level)
    os.environ["TRANSFORMATION_WORKBENCH_LOG_LEVEL"] = (
        "INFO" if verbose else "WARNING"
    )


def _validation_message(exc: ValidationError) -> str:
    error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in error.get("loc", ()))
    message = str(error.get("msg", "Intake validation failed."))
    return f"{location}: {message}" if location else message


def _fail(code: str, message: str) -> None:
    print(
        json.dumps(
            {"error": {"code": code, "message": message}},
            indent=2,
        )
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
