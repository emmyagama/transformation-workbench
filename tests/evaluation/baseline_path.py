"""Minimal non-delegating baseline for the Level 2 comparison.

This is an evaluation harness, not a second product architecture. It reuses the
same read-only evidence source, typed contracts, validators, and deterministic
solution designer as the A2A path, but it calls them directly without specialist
discovery or task exchange.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from transformation_workbench.a2a.claims import UnsupportedClaimError
from transformation_workbench.a2a.contracts import EvidencePack, SolutionOptions
from transformation_workbench.a2a.evidence_source import (
    EvidenceSource,
    EvidenceSourceError,
    McpEvidenceSource,
)
from transformation_workbench.a2a.solution_designer import design_options
from transformation_workbench.a2a.validation import (
    ContractValidationError,
    validate_evidence_pack,
    validate_solution_options,
    verify_evidence_against_fixture,
)

OptionsMutator = Callable[[SolutionOptions], SolutionOptions]


@dataclass(frozen=True)
class BaselineOutcome:
    status: str
    error_code: str | None
    evidence_pack: EvidencePack | None
    solution_options: SolutionOptions | None
    attempts: int = 1


async def run_baseline(
    request_id: str,
    case_ids: Sequence[str],
    *,
    source: EvidenceSource | None = None,
    timeout: float = 20.0,
    options_mutator: OptionsMutator | None = None,
) -> BaselineOutcome:
    """Run the direct evidence-to-options path once.

    The path has no A2A discovery, no specialist tasks, and no protocol trace.
    It applies the same validation order as the coordinator.
    """
    normalized = list(case_ids)
    evidence_source = source or McpEvidenceSource(timeout=timeout)
    try:
        pack = await evidence_source.collect(request_id, normalized)
        validate_evidence_pack(pack, expected_request_id=request_id)
        if (
            set(pack.requested_case_ids) != set(normalized)
            or len(pack.requested_case_ids) != len(normalized)
        ):
            raise ContractValidationError(
                "case_set_mismatch",
                "Evidence pack requested case set does not match the request.",
            )
        verify_evidence_against_fixture(pack)
        options = design_options(pack)
        if options_mutator is not None:
            options = options_mutator(options)
        validate_solution_options(options, pack)
        return BaselineOutcome(
            status="complete",
            error_code=None,
            evidence_pack=pack,
            solution_options=options,
        )
    except (
        EvidenceSourceError,
        ContractValidationError,
        UnsupportedClaimError,
        ValidationError,
        ValueError,
    ) as exc:
        return BaselineOutcome(
            status="failure",
            error_code=getattr(exc, "code", type(exc).__name__),
            evidence_pack=None,
            solution_options=None,
        )
