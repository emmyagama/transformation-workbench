"""Run the complete pinned Open Responses suite once against the local adapter."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from transformation_workbench.openresponses_adapter.compaction import COMPACTION_KEY_ENV
from transformation_workbench.openresponses_adapter.gateway import (
    ConfigurationError,
    assert_loopback_url,
)
from transformation_workbench.openresponses_adapter.runtime import HOSTED_CREDENTIAL_ENV

SUITE_PATH = Path(
    os.environ.get(
        "OPENRESPONSES_SUITE_PATH",
        "openresponses-suite-2d2f551085ea40678a659c5c204a9ab4",
    )
)
SUITE_COMMIT = "dce9ddb91921427c2ba06901c7dfaf0cc7056799"
BUN_PATH = Path(os.environ.get("OPENRESPONSES_BUN_PATH", "bun"))
DEFAULT_OUTPUT = Path("docs/evidence/week4-openresponses-gate3.json")
DEFAULT_GATEWAY_URL = "http://127.0.0.1:8000"
DEFAULT_MODEL = "gpt-6.1-sol"
LOCAL_API_KEY = "local-test-token"
PRIOR_CONSERVATIVE_OPERATIONS = 31
SUITE_OPERATION_BUDGET = 23
TOTAL_OPERATION_CEILING = 56
CONTINGENCY_RESERVE = 2
EXPECTED_UPSTREAM_OPERATIONS = {
    "basic-response": 1,
    "assistant-phase": 1,
    "response-output-phase-schema": 0,
    "streaming-response": 1,
    "websocket-response": 1,
    "websocket-sequential-responses": 2,
    "websocket-continuation": 2,
    "websocket-reconnect-store-false-recovery": 2,
    "websocket-previous-response-not-found": 0,
    "websocket-failed-continuation-evicts-cache": 2,
    "websocket-compact-new-chain": 2,
    "system-prompt": 1,
    "tool-calling": 1,
    "image-input": 1,
    "multi-turn": 1,
    "compact-response": 1,
    "compact-missing-model": 0,
}
ZERO_UPSTREAM_TESTS = {
    test_id
    for test_id, count in EXPECTED_UPSTREAM_OPERATIONS.items()
    if count == 0
}
TEST_IDS = (
    "basic-response",
    "assistant-phase",
    "response-output-phase-schema",
    "streaming-response",
    "websocket-response",
    "websocket-sequential-responses",
    "websocket-continuation",
    "websocket-reconnect-store-false-recovery",
    "websocket-previous-response-not-found",
    "websocket-failed-continuation-evicts-cache",
    "websocket-compact-new-chain",
    "system-prompt",
    "tool-calling",
    "image-input",
    "multi-turn",
    "compact-response",
    "compact-missing-model",
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _find_bun() -> Path:
    if BUN_PATH.is_file():
        return BUN_PATH
    found = shutil.which("bun")
    if found:
        return Path(found)
    raise RuntimeError("Bun executable was not found.")


def _verify_suite(suite: Path) -> None:
    if not suite.is_dir():
        raise RuntimeError(f"Pinned suite directory is missing: {suite}")
    commit = _git(suite, "rev-parse", "HEAD")
    if commit != SUITE_COMMIT:
        raise RuntimeError(
            f"Pinned suite commit mismatch: expected {SUITE_COMMIT}, got {commit}"
        )
    dirty = _git(suite, "status", "--porcelain")
    if dirty:
        raise RuntimeError("Pinned suite has local modifications; refusing to run.")


def _verify_filter_behavior(suite: Path) -> None:
    source = (suite / "bin" / "compliance-test.ts").read_text(encoding="utf-8")
    required = (
        "testTemplates.filter((template) => args.filter?.includes(template.id))",
        "runAllTests(config, onProgress, selectedTemplates)",
        "if (args.filter && !args.filter.includes(result.id))",
    )
    missing = [fragment for fragment in required if fragment not in source]
    if missing:
        raise RuntimeError(
            "Pinned CLI filter could not be verified; refusing to run."
        )


def _verify_suite_environment() -> None:
    configured = [
        name for name in HOSTED_CREDENTIAL_ENV if os.environ.get(name)
    ]
    if os.environ.get(COMPACTION_KEY_ENV):
        configured.append(COMPACTION_KEY_ENV)
    if configured:
        raise RuntimeError(
            "Suite runner environment contains secret variables: "
            + ", ".join(sorted(set(configured)))
        )


def _repo_state(repo: Path) -> dict[str, Any]:
    try:
        head = _git(repo, "rev-parse", "HEAD")
        dirty = _git(repo, "status", "--porcelain")
    except subprocess.SubprocessError:
        return {"head": None, "dirty": None}
    return {"head": head, "dirty": bool(dirty)}


def _gateway_json(
    client: httpx.Client,
    gateway_url: str,
    path: str,
    method: str = "GET",
) -> dict[str, Any]:
    response = client.request(method, f"{gateway_url}{path}")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"Adapter returned non-object JSON for {path}.")
    return payload


def _wait_for_gateway(gateway_url: str, timeout_seconds: float = 30.0) -> None:
    with httpx.Client(trust_env=False, timeout=5.0) as client:
        deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds
        last_error: Exception | None = None
        while datetime.now(timezone.utc).timestamp() < deadline:
            try:
                health = _gateway_json(client, gateway_url, "/__local/health")
                if health.get("status") == "ok":
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"Adapter health check did not become ready: {last_error}")


def _run_one(
    bun: Path,
    suite: Path,
    gateway_url: str,
    model: str,
    api_key: str,
    test_id: str,
) -> dict[str, Any]:
    command = [
        str(bun),
        "run",
        "bin/compliance-test.ts",
        "--base-url",
        gateway_url,
        "--api-key",
        api_key,
        "--model",
        model,
        "--filter",
        test_id,
        "--json",
    ]
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in HOSTED_CREDENTIAL_ENV and name != COMPACTION_KEY_ENV
    }
    env["NO_COLOR"] = "1"
    try:
        completed = subprocess.run(
            command,
            cwd=suite,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "id": test_id,
            "status": "harness_error",
            "errors": ["Timed out after 120 seconds."],
            "duration_ms": None,
            "stream_events": None,
            "suite_summary": None,
            "filter_isolated": False,
        }
    if completed.returncode != 0:
        return {
            "id": test_id,
            "status": "harness_error",
            "errors": [
                f"CLI exited with {completed.returncode}.",
                completed.stderr.strip()[:1000],
            ],
            "duration_ms": None,
            "stream_events": None,
            "suite_summary": None,
            "filter_isolated": False,
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "id": test_id,
            "status": "harness_error",
            "errors": ["CLI output was not valid JSON."],
            "duration_ms": None,
            "stream_events": None,
            "suite_summary": None,
            "filter_isolated": False,
        }
    results = payload.get("results")
    if not isinstance(results, list) or len(results) != 1:
        return {
            "id": test_id,
            "status": "harness_error",
            "errors": ["CLI filter did not isolate exactly one test."],
            "duration_ms": None,
            "stream_events": None,
            "suite_summary": payload.get("summary"),
            "filter_isolated": False,
        }
    result = results[0]
    if result.get("id") != test_id:
        return {
            "id": test_id,
            "status": "harness_error",
            "errors": ["CLI ran a different test than requested."],
            "duration_ms": None,
            "stream_events": None,
            "suite_summary": payload.get("summary"),
            "filter_isolated": False,
        }
    return {
        "id": test_id,
        "status": result.get("status"),
        "errors": result.get("errors") or [],
        "duration_ms": result.get("duration"),
        "stream_events": result.get("streamEvents"),
        "suite_summary": payload.get("summary"),
        "filter_isolated": True,
    }


def _run(
    bun: Path,
    suite: Path,
    repo: Path,
    gateway_url: str,
    model: str,
    api_key: str,
    output: Path,
    suite_budget: int,
    prior_operations: int,
    total_ceiling: int,
    reserve: int,
) -> int:
    _wait_for_gateway(gateway_url)
    rows: list[dict[str, Any]] = []
    cumulative = 0
    budget_exceeded = False
    accounting_errors: list[str] = []

    with httpx.Client(trust_env=False, timeout=10.0) as client:
        initial = _gateway_json(client, gateway_url, "/__local/stats")
        if initial.get("upstream_requests") != 0:
            raise RuntimeError(
                "Adapter already recorded upstream operations; refusing to run."
            )
        for test_id in TEST_IDS:
            anticipated = EXPECTED_UPSTREAM_OPERATIONS[test_id]
            if cumulative + anticipated > suite_budget:
                budget_exceeded = True
                break
            _gateway_json(client, gateway_url, "/__local/stats/reset", "POST")
            row = _run_one(bun, suite, gateway_url, model, api_key, test_id)
            operations = _gateway_json(client, gateway_url, "/__local/stats")
            row["adapter_operations"] = operations
            used = operations.get("upstream_requests")
            if not isinstance(used, int) or used < 0:
                raise RuntimeError("Adapter returned invalid operation accounting.")
            cumulative += used
            if used > anticipated:
                row["status"] = "accounting_error"
                accounting_errors.append(
                    f"{test_id} made {used} upstream operation(s); "
                    f"expected at most {anticipated}."
                )
            if test_id in ZERO_UPSTREAM_TESTS and used != 0:
                row["status"] = "accounting_error"
                accounting_errors.append(
                    f"{test_id} made {used} upstream operation(s); expected 0."
                )
            rows.append(row)
            print(
                f"{test_id}: {row['status']} "
                f"operations={used} "
                f"cumulative={cumulative} "
                f"duration_ms={row['duration_ms']}",
                flush=True,
            )
            if cumulative > suite_budget:
                budget_exceeded = True
                print(
                    "Budget exceeded; stopping before any further suite test.",
                    flush=True,
                )
                break

    passed = sum(1 for row in rows if row["status"] == "passed")
    failed = sum(1 for row in rows if row["status"] == "failed")
    harness_errors = sum(
        1 for row in rows if row["status"] in {"harness_error", "accounting_error"}
    )
    conservative_total = prior_operations + cumulative
    reserve_remaining = total_ceiling - conservative_total
    within_ceiling = conservative_total <= total_ceiling
    within_reserve = reserve_remaining >= reserve
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": {"path": str(suite), "commit": SUITE_COMMIT},
        "adapter": {
            "model": model,
            "gateway_url": gateway_url,
            "transport": "localhost-adapter-to-console-upstream",
            "repo": _repo_state(repo),
        },
        "summary": {
            "passed": passed,
            "failed": failed,
            "harness_errors": harness_errors,
            "total": len(rows),
            "executed_tests": [row["id"] for row in rows],
            "filter_isolated": all(row["filter_isolated"] for row in rows),
            "retries": 0,
            "credential_environment_secret_free": True,
            "budget_exceeded": budget_exceeded,
            "accounting_errors": accounting_errors,
        },
        "operation_accounting": {
            "prior_conservative_operations": prior_operations,
            "suite_operations": cumulative,
            "suite_operation_budget": suite_budget,
            "conservative_total": conservative_total,
            "total_ceiling": total_ceiling,
            "contingency_reserve": reserve,
            "reserve_remaining": reserve_remaining,
            "within_ceiling": within_ceiling,
            "within_reserve": within_reserve,
            "within_suite_budget": cumulative <= suite_budget,
        },
        "tests": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"evidence={output}", flush=True)
    ok = (
        passed == len(TEST_IDS)
        and harness_errors == 0
        and not budget_exceeded
        and within_ceiling
        and within_reserve
        and cumulative <= suite_budget
    )
    return 0 if ok else 1


def _verify_httpx_support() -> None:
    if importlib.util.find_spec("httpx") is None:
        raise RuntimeError("httpx is not installed.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete pinned suite once against the local adapter."
    )
    parser.add_argument("--suite", type=Path, default=SUITE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key", default=LOCAL_API_KEY)
    parser.add_argument("--prior-operations", type=int, default=PRIOR_CONSERVATIVE_OPERATIONS)
    parser.add_argument("--total-ceiling", type=int, default=TOTAL_OPERATION_CEILING)
    parser.add_argument("--reserve", type=int, default=CONTINGENCY_RESERVE)
    args = parser.parse_args(argv)

    try:
        gateway_url = assert_loopback_url(args.gateway_url, field="gateway")
        _verify_suite_environment()
        _verify_suite(args.suite)
        _verify_filter_behavior(args.suite)
        _verify_httpx_support()
        bun = _find_bun()
        repo = Path(__file__).resolve().parents[1]
        if args.prior_operations + SUITE_OPERATION_BUDGET + args.reserve > args.total_ceiling:
            raise RuntimeError("Operation budget allocation exceeds the ceiling.")
    except (ConfigurationError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return _run(
        bun,
        args.suite,
        repo,
        gateway_url,
        args.model,
        args.api_key,
        args.output,
        SUITE_OPERATION_BUDGET,
        args.prior_operations,
        args.total_ceiling,
        args.reserve,
    )


if __name__ == "__main__":
    raise SystemExit(main())
