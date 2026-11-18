"""Run the pinned Open Responses compliance suite against local fakes only."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transformation_workbench.openresponses_adapter.compaction import (
    COMPACTION_KEY_ENV,
    CompactionCipher,
)
from transformation_workbench.openresponses_adapter.fake_upstream import build_fake_app
from transformation_workbench.openresponses_adapter.gateway import (
    ConfigurationError,
    assert_loopback_url,
    build_gateway_app,
)
from transformation_workbench.openresponses_adapter.runtime import (
    HOSTED_CREDENTIAL_ENV,
    assert_no_hosted_credentials,
    serve_loopback,
)

SUITE_PATH = Path(
    os.environ.get(
        "OPENRESPONSES_SUITE_PATH",
        "openresponses-suite-2d2f551085ea40678a659c5c204a9ab4",
    )
)
SUITE_COMMIT = "dce9ddb91921427c2ba06901c7dfaf0cc7056799"
BUN_PATH = Path(os.environ.get("OPENRESPONSES_BUN_PATH", "bun"))
DEFAULT_OUTPUT = Path("docs/evidence/openresponses-gate2.json")
MODEL = "local-fake-model"
API_KEY = "local-dummy-key"
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


def _git(suite: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(suite), *args],
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


def _verify_optional_support() -> None:
    if importlib.util.find_spec("wsproto") is None and importlib.util.find_spec(
        "websockets"
    ) is None:
        raise RuntimeError(
            "No WebSocket implementation is installed for uvicorn; "
            "install the openresponses extra."
        )
    if importlib.util.find_spec("cryptography") is None:
        raise RuntimeError(
            "The cryptography package is not installed; "
            "install the openresponses extra."
        )


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


def _run_one(
    bun: Path,
    suite: Path,
    gateway_url: str,
    test_id: str,
) -> dict[str, Any]:
    command = [
        str(bun),
        "run",
        "bin/compliance-test.ts",
        "--base-url",
        gateway_url,
        "--api-key",
        API_KEY,
        "--model",
        MODEL,
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
            timeout=60,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "id": test_id,
            "status": "harness_error",
            "errors": ["Timed out after 60 seconds."],
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


async def _run(
    bun: Path,
    suite: Path,
    output: Path,
) -> int:
    fake_app = build_fake_app()
    stats = fake_app.state.fake_stats
    cipher = CompactionCipher(secrets.token_bytes(32))
    gateway_holder: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []

    def gateway_factory(_gateway_url: str) -> Any:
        app = build_gateway_app(
            fake_url,
            timeout=30.0,
            compaction_cipher=cipher,
        )
        gateway_holder["app"] = app
        return app

    async with serve_loopback(lambda _: fake_app) as fake_url:
        assert_loopback_url(fake_url, field="fake upstream")
        async with serve_loopback(gateway_factory) as gateway_url:
            assert_loopback_url(gateway_url, field="gateway")
            gateway_stats = gateway_holder["app"].state.gateway_stats
            for test_id in TEST_IDS:
                stats.reset()
                gateway_stats.reset()
                row = await asyncio.to_thread(
                    _run_one,
                    bun,
                    suite,
                    gateway_url,
                    test_id,
                )
                row["fake_upstream"] = stats.snapshot()
                row["adapter_operations"] = gateway_stats.snapshot()
                rows.append(row)
                counts = row["fake_upstream"]
                operations = row["adapter_operations"]
                print(
                    f"{test_id}: {row['status']} "
                    f"requests={counts['requests']} "
                    f"turns={counts['response_turns']} "
                    f"compactions={counts['compact_requests']} "
                    f"operations={operations['upstream_requests']} "
                    f"duration_ms={row['duration_ms']}",
                    flush=True,
                )

    passed = sum(1 for row in rows if row["status"] == "passed")
    failed = sum(1 for row in rows if row["status"] == "failed")
    harness_errors = sum(1 for row in rows if row["status"] == "harness_error")
    total_operations = sum(
        row["adapter_operations"]["upstream_requests"] for row in rows
    )
    expected_operations = 19
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": {"path": str(suite), "commit": SUITE_COMMIT},
        "adapter": {"model": MODEL, "transport": "local-fake-upstream"},
        "summary": {
            "passed": passed,
            "failed": failed,
            "harness_errors": harness_errors,
            "total": len(rows),
            "filter_isolated": all(row["filter_isolated"] for row in rows),
            "total_adapter_upstream_operations": total_operations,
            "expected_adapter_upstream_operations": expected_operations,
            "operation_budget_match": total_operations == expected_operations,
        },
        "tests": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"evidence={output}", flush=True)
    return 0 if passed == len(TEST_IDS) and harness_errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run pinned Open Responses suite against a local fake only."
    )
    parser.add_argument("--suite", type=Path, default=SUITE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    try:
        assert_no_hosted_credentials()
        _verify_suite(args.suite)
        _verify_filter_behavior(args.suite)
        _verify_optional_support()
        bun = _find_bun()
    except (ConfigurationError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return asyncio.run(_run(bun, args.suite, args.output))


if __name__ == "__main__":
    raise SystemExit(main())
