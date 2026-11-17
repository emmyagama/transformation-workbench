"""Command-line runner for the local A2A coordinator."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence

from .claims import UnsupportedClaimError
from .local_runtime import run_local_diagnosis
from .phase2_coordinator import CoordinatorError
from .summary import SummaryError, render_summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one local loopback A2A diagnosis.",
    )
    parser.add_argument(
        "--request-id",
        required=True,
        help="Non-empty correlation ID for this run.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        dest="case_ids",
        help="Synthetic case ID to inspect; repeat for multiple IDs.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Per-operation A2A timeout in seconds.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Bounded transient retry count.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Print the structured result or the deterministic user-facing report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        result = asyncio.run(
            run_local_diagnosis(
                args.request_id,
                args.case_ids,
                timeout=args.timeout,
                max_retries=args.max_retries,
            )
        )
        if args.format == "markdown":
            output = render_summary(result).rendered_markdown
        else:
            output = json.dumps(result.model_dump(mode="json"), indent=2)
    except (CoordinatorError, SummaryError, UnsupportedClaimError) as exc:
        print(
            json.dumps(
                {
                    "error": {
                        "code": getattr(exc, "code", "unsupported_claim"),
                        "message": getattr(exc, "message", str(exc)),
                    }
                },
                indent=2,
            )
        )
        raise SystemExit(1) from exc
    if args.format == "markdown":
        print(output, end="")
        return
    print(output)


if __name__ == "__main__":
    main()
