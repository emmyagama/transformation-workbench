"""Read-only Goose-facing MCP entry point for the A2A coordinator."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from .a2a.contracts import (
    Calculation,
    CoordinatorResult,
    EvidencePack,
    ProtocolTraceEvent,
    SolutionOption,
    SolutionOptions,
)
from .a2a.local_runtime import run_local_diagnosis
from .a2a.phase2_coordinator import CoordinatorError
from .a2a.summary import CoordinatorSummary, SummaryError, render_summary

logger = logging.getLogger(__name__)

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True,
    open_world_hint=False,
)

_CACHE: dict[str, tuple[str, CoordinatorResult]] = {}
_CACHE_LOCK = threading.Lock()


class CoordinatorDiagnosis(BaseModel):
    """MCP-facing coordinator result without computed-field schema drift."""

    request_id: str
    status: Literal["complete"] = "complete"
    measured_facts: EvidencePack
    calculations: list[Calculation]
    assumptions: list[str]
    solution_options: SolutionOptions
    recommendations: list[SolutionOption]
    trace: list[ProtocolTraceEvent]
    summary: CoordinatorSummary

    @classmethod
    def from_result(cls, result: CoordinatorResult) -> "CoordinatorDiagnosis":
        return cls(
            request_id=result.request_id,
            measured_facts=result.measured_facts,
            calculations=result.calculations,
            assumptions=result.assumptions,
            solution_options=result.solution_options,
            recommendations=result.recommendations,
            trace=result.trace,
            summary=render_summary(result),
        )


mcp = MCPServer(
    name="Transformation Workbench A2A Coordinator",
    version="0.1.0",
    instructions=(
        "Read-only local A2A coordinator. Exposes only run_a2a_diagnosis. "
        "The coordinator starts loopback specialists, performs real A2A task "
        "exchanges, validates typed handoffs, and returns a sanitized result. "
        "No Workbench tools, filesystem paths, writes, or external actions are "
        "exposed in this session."
    ),
)


@mcp.tool(structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
def run_a2a_diagnosis(
    request_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Non-empty correlation ID for one diagnosis run.",
        ),
    ],
    case_ids: Annotated[
        list[str] | str | None,
        Field(
            description=(
                "Optional synthetic case IDs to inspect, such as C-009. "
                "Provide a JSON array or a comma-separated string. "
                "At most 20 unique IDs are accepted."
            )
        ),
    ] = None,
) -> CoordinatorDiagnosis:
    """Run one read-only Evidence-to-Options A2A diagnosis."""
    cleaned_request_id = request_id.strip()
    normalized_case_ids = _normalize_case_ids_input(case_ids)
    fingerprint = ",".join(normalized_case_ids)
    logger.info("tool=run_a2a_diagnosis request_id=%r", cleaned_request_id)

    with _CACHE_LOCK:
        cached = _CACHE.get(cleaned_request_id)
        if cached is not None:
            cached_fingerprint, cached_result = cached
            if cached_fingerprint != fingerprint:
                raise ToolError(
                    "request_conflict: Duplicate request_id was replayed "
                    "with different inputs."
                )
            replay = cached_result.model_copy(
                update={
                    "trace": [
                        *cached_result.trace,
                        ProtocolTraceEvent(
                            step="duplicate_replay",
                            agent="coordinator",
                            method="NONE",
                            path="(cached result)",
                            skill_id="duplicate_request_guard",
                        ),
                    ]
                }
            )
            return CoordinatorDiagnosis.from_result(replay)

        try:
            result = asyncio.run(
                run_local_diagnosis(cleaned_request_id, normalized_case_ids)
            )
            diagnosis = CoordinatorDiagnosis.from_result(result)
        except CoordinatorError as exc:
            raise ToolError(f"{exc.code}: {exc.message}") from exc
        except SummaryError as exc:
            raise ToolError(f"{exc.code}: {exc.message}") from exc
        except Exception as exc:
            logger.warning("A2A diagnosis failed: %s", type(exc).__name__)
            raise ToolError(
                f"coordinator_error: {type(exc).__name__}"
            ) from exc
        _CACHE[cleaned_request_id] = (fingerprint, result)
        return diagnosis


def _normalize_case_ids_input(
    value: list[str] | str | None,
) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return _clean_ids(parsed)
            text = text.strip("[]")
        return _clean_ids(text.split(","))
    return _clean_ids(value)


def _clean_ids(values: list[object]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        item = str(value).strip().strip("'\"")
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
    logger.info("Starting Transformation Workbench A2A coordinator MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
