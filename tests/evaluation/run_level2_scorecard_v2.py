"""Run every frozen Level 2 V2 case and write a literal-code scorecard.

Every workflow-labeled variant is executed through ``run_workflow``. Every
coordinator-labeled variant is executed through the real local coordinator. The
runner records path-specific terminal and cause codes, semantic failure
invariants, retry counts, and a sanitized protocol trace for every case.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from tests.evaluation.level2_v2_common import (
    OUTPUT_DIR,
    SHARED_CASES,
    load_corpus,
    load_manifest,
    make_row,
    run_baseline_path,
    run_entrypoint,
    score_path,
    validate_corpus_routing,
)


async def main() -> None:
    corpus = load_corpus()
    manifest = load_manifest()
    validate_corpus_routing(corpus)
    rows: list[dict[str, Any]] = []
    for case in corpus["cases"]:
        for variant in case["variants"]:
            entrypoint, outcome = run_entrypoint(case, variant)
            if asyncio.iscoroutine(outcome):
                outcome = await outcome
            observed = score_path(variant, outcome, manifest)
            baseline = None
            if variant["variant_id"] in SHARED_CASES:
                baseline_outcome = await run_baseline_path(variant)
                baseline = score_path(
                    variant,
                    baseline_outcome,
                    manifest,
                    expected_key="baseline_expected",
                )
            row = make_row(case, variant, observed, baseline)
            rows.append(row)
            if entrypoint != row["runner_entrypoint"]:
                raise ValueError(
                    f"runner label mismatch: {row['runner_entrypoint']} != "
                    f"{entrypoint}"
                )

    misses = [row for row in rows if not row["passed"]]
    terminal_matches = sum(
        1 for row in rows if row["terminal_code"] == row["expected"]["terminal_code"]
    )
    cause_matches = sum(
        1 for row in rows if row["cause_code"] == row["expected"]["cause_code"]
    )
    all_invariants_scored = all(
        set(row["expected"]["invariants"]) <= set(row["dimensions"])
        for row in rows
    )
    report = {
        "pack_id": corpus["pack_id"],
        "pack_version": corpus["pack_version"],
        "scorecard_version": "2.0.0",
        "baseline_commit": corpus["baseline_commit"],
        "source_commit": corpus["source_commit"],
        "matching_policy": corpus["matching_policy"],
        "variant_count": len(rows),
        "workflow_variant_count": sum(
            1 for row in rows if row["runner_entrypoint"] == "workflow"
        ),
        "coordinator_variant_count": sum(
            1 for row in rows if row["runner_entrypoint"] == "coordinator"
        ),
        "terminal_code_matches": terminal_matches,
        "cause_code_matches": cause_matches,
        "all_declared_invariants_scored": all_invariants_scored,
        "passed": len(rows) - len(misses),
        "missed": len(misses),
        "rows": rows,
        "notes": [
            "V2 supersedes the V1 scored run; V1 remains a historical artifact.",
            "Every workflow-labeled variant uses the real run_workflow entrypoint.",
            "Every coordinator-labeled variant uses the real local Phase2Coordinator.",
            "Terminal and cause expectations are literal and path-specific; union matching is not used.",
            "Each row records terminal code, cause code, failure category, retry count, human-judgment flag, and a sanitized trace.",
            "The L2-04b workflow expectation is task_failure / request_mismatch; the direct baseline expectation is request_mismatch / no cause.",
            "Whole-workflow failure remains the policy; no partial-result status exists.",
            "No hosted model, provider, external system, credential, or real data is used.",
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "scorecard-v2.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Level 2 per-case scorecard v2",
        "",
        f"**Pack:** `{report['pack_id']}` v{report['pack_version']}",
        f"**Source commit:** `{report['source_commit']}`",
        f"**Matching policy:** `{report['matching_policy']}`",
        "",
        "## Summary",
        "",
        f"- Variants: **{report['variant_count']}**",
        f"- Workflow variants: **{report['workflow_variant_count']}**",
        f"- Coordinator variants: **{report['coordinator_variant_count']}**",
        f"- Passed: **{report['passed']}**",
        f"- Missed: **{report['missed']}**",
        f"- Literal terminal-code matches: **{report['terminal_code_matches']}/{report['variant_count']}**",
        f"- Literal cause-code matches: **{report['cause_code_matches']}/{report['variant_count']}**",
        f"- All declared invariants scored: **{report['all_declared_invariants_scored']}**",
        "",
        "## Per-case results",
        "",
        "| Case | Variant | Entrypoint | Status | Terminal / cause | Category | Attempts | Human judgment | Pass | Failed invariants |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        failed = row["miss"]
        terminal = row["terminal_code"] or "-"
        cause = row["cause_code"] or "-"
        lines.append(
            f"| {row['case_id']} | {row['variant_id']} | {row['runner_entrypoint']} | "
            f"{row['status']} | {terminal} / {cause} | "
            f"{row['failure_category'] or '-'} | {row['retry_count']} | "
            f"{row['human_judgment']} | {row['passed']} | "
            f"{', '.join(failed) if failed else '-'} |"
        )
    lines.extend(["", "## Misses", ""])
    if misses:
        for row in misses:
            lines.append(f"- **{row['variant_id']}:** {', '.join(row['miss'])}")
    else:
        lines.append("No misses under the frozen V2 path-specific expectations.")
    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")
    (OUTPUT_DIR / "scorecard-v2.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "variant_count": report["variant_count"],
                "passed": report["passed"],
                "missed": report["missed"],
                "terminal_code_matches": report["terminal_code_matches"],
                "cause_code_matches": report["cause_code_matches"],
                "all_declared_invariants_scored": report[
                    "all_declared_invariants_scored"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
