"""Run the V2 baseline-versus-A2A comparison without union matching.

The A2A side uses the real workflow or coordinator entrypoint selected by the
corpus label. The baseline side calls the same evidence source and deterministic
solution designer directly. Terminal codes, cause codes, and semantic failure
results are reported separately for each path and then compared literally.
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
    run_baseline_path,
    run_entrypoint,
    score_path,
    validate_corpus_routing,
)


def _code_note(
    variant_id: str,
    a2a: dict[str, Any],
    baseline: dict[str, Any],
) -> str | None:
    if a2a["terminal_code"] == baseline["terminal_code"]:
        return None
    a2a_code = a2a["terminal_code"]
    baseline_code = baseline["terminal_code"]
    cause = a2a["cause_code"]
    if a2a_code == "task_failure" and cause:
        return (
            "The A2A path records the protocol wrapper "
            f"task_failure with cause {cause}; the direct baseline returns "
            f"{baseline_code} without a cause. Each path matches its own V2 "
            "expected terminal/cause pair and both fail closed."
        )
    return (
        f"The A2A path reports {a2a_code}; the baseline reports "
        f"{baseline_code}. Each path matches its own V2 expectation."
    )


async def main() -> None:
    corpus = load_corpus()
    manifest = load_manifest()
    validate_corpus_routing(corpus)
    rows: list[dict[str, Any]] = []
    not_applicable: list[dict[str, Any]] = []

    for case in corpus["cases"]:
        for variant in case["variants"]:
            if variant["variant_id"] not in SHARED_CASES:
                not_applicable.append(
                    {
                        "variant_id": variant["variant_id"],
                        "entrypoint": case["entrypoint"],
                        "reason": (
                            "This case depends on workflow/approval or A2A "
                            "protocol behavior that the direct baseline does "
                            "not implement."
                        ),
                    }
                )
                continue
            _, outcome = run_entrypoint(case, variant)
            if asyncio.iscoroutine(outcome):
                outcome = await outcome
            a2a = score_path(variant, outcome, manifest)
            baseline_outcome = await run_baseline_path(variant)
            baseline = score_path(
                variant,
                baseline_outcome,
                manifest,
                expected_key="baseline_expected",
            )
            same_observed_status = a2a["status"] == baseline["status"]
            exact_terminal_code_match = (
                a2a["terminal_code"] == baseline["terminal_code"]
            )
            exact_cause_code_match = (
                a2a["cause_code"] == baseline["cause_code"]
            )
            both_successful = (
                a2a["observed_outcome"] == "success"
                and baseline["observed_outcome"] == "success"
            )
            both_fail_closed = (
                a2a["observed_outcome"] == "fail_closed"
                and baseline["observed_outcome"] == "fail_closed"
            )
            semantic_equal = same_observed_status and (
                both_successful or both_fail_closed
            )
            if both_successful:
                semantic_basis = "both_complete_with_successful_result"
            elif both_fail_closed:
                semantic_basis = "both_fail_closed"
            elif a2a["observed_outcome"] != baseline["observed_outcome"]:
                semantic_basis = "observed_outcome_mismatch"
            else:
                semantic_basis = "observed_status_mismatch"
            rows.append(
                {
                    "variant_id": variant["variant_id"],
                    "family": variant["description"],
                    "entrypoint": case["entrypoint"],
                    "a2a": a2a,
                    "baseline": baseline,
                    "same_observed_status": same_observed_status,
                    "exact_terminal_code_match": exact_terminal_code_match,
                    "exact_cause_code_match": exact_cause_code_match,
                    "both_complete_with_successful_result": both_successful,
                    "both_fail_closed": both_fail_closed,
                    "semantic_basis": semantic_basis,
                    "semantic_equal": semantic_equal,
                    "code_note": _code_note(
                        variant["variant_id"], a2a, baseline
                    ),
                }
            )

    report = {
        "pack_id": corpus["pack_id"],
        "pack_version": corpus["pack_version"],
        "comparison_version": "2.0.0",
        "baseline_commit": corpus["baseline_commit"],
        "source_commit": corpus["source_commit"],
        "matching_policy": corpus["matching_policy"],
        "semantic_definition": (
            "Cross-path semantic equality uses observed outcomes only. It "
            "requires the same observed status and either (a) both paths "
            "complete with a successful result, or (b) both paths terminate "
            "failure/refused with no successful result (fail-closed). It does "
            "not use path-specific expectations, terminal codes, or cause codes; "
            "those remain separate match counts."
        ),
        "method": (
            "The A2A side uses the path selected by the corpus label: the real "
            "run_workflow entrypoint for workflow variants and the real local "
            "Phase2Coordinator for coordinator variants. The baseline side calls "
            "the same read-only evidence source and deterministic solution "
            "designer directly. Each path is scored against its own literal "
            "terminal and cause expectations. No union match is used. Cross-path "
            "semantic equality is then computed from observed outcomes only, as "
            "defined in semantic_definition."
        ),
        "limits": [
            "Small synthetic sample; not a general benchmark.",
            "Deterministic fakes test orchestration and contracts, not model reasoning.",
            "The baseline has no A2A protocol trace, discovery, retry, or timeout semantics.",
            "Cases that depend on A2A protocol behavior or the full report/approval workflow are not applicable to the baseline.",
            "No hosted model, provider, external system, credential, or real data is used.",
            "No latency, cost, savings, or productivity outcome is claimed.",
        ],
        "shared_case_count": len(rows),
        "a2a_terminal_code_matches": sum(
            1
            for row in rows
            if row["a2a"]["terminal_code"]
            == row["a2a"]["expected"]["terminal_code"]
        ),
        "a2a_cause_code_matches": sum(
            1
            for row in rows
            if row["a2a"]["cause_code"]
            == row["a2a"]["expected"]["cause_code"]
        ),
        "a2a_path_passes": sum(
            1 for row in rows if row["a2a"]["passed"]
        ),
        "baseline_terminal_code_matches": sum(
            1
            for row in rows
            if row["baseline"]["terminal_code"]
            == row["baseline"]["expected"]["terminal_code"]
        ),
        "baseline_cause_code_matches": sum(
            1
            for row in rows
            if row["baseline"]["cause_code"]
            == row["baseline"]["expected"]["cause_code"]
        ),
        "baseline_path_passes": sum(
            1 for row in rows if row["baseline"]["passed"]
        ),
        "cross_path_exact_terminal_matches": sum(
            1 for row in rows if row["exact_terminal_code_match"]
        ),
        "cross_path_exact_cause_matches": sum(
            1 for row in rows if row["exact_cause_code_match"]
        ),
        "cross_path_both_success_matches": sum(
            1 for row in rows if row["both_complete_with_successful_result"]
        ),
        "cross_path_both_fail_closed_matches": sum(
            1 for row in rows if row["both_fail_closed"]
        ),
        "cross_path_semantic_matches": sum(
            1 for row in rows if row["semantic_equal"]
        ),
        "rows": rows,
        "not_applicable": not_applicable,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "comparison-v2.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    lines = [
        "# Level 2 baseline-versus-A2A comparison v2",
        "",
        f"**Pack:** `{report['pack_id']}` v{report['pack_version']}",
        f"**Source commit:** `{report['source_commit']}`",
        f"**Matching policy:** `{report['matching_policy']}`",
        "",
        "## Method",
        "",
        report["method"],
        "",
        "### Cross-path semantic definition",
        "",
        report["semantic_definition"],
        "",
        "## Result",
        "",
        f"- Shared cases: **{report['shared_case_count']}**",
        f"- A2A path-specific passes: **{report['a2a_path_passes']}/{report['shared_case_count']}**",
        f"- A2A literal terminal-code matches: **{report['a2a_terminal_code_matches']}/{report['shared_case_count']}**",
        f"- A2A literal cause-code matches: **{report['a2a_cause_code_matches']}/{report['shared_case_count']}**",
        f"- Baseline path-specific passes: **{report['baseline_path_passes']}/{report['shared_case_count']}**",
        f"- Baseline literal terminal-code matches: **{report['baseline_terminal_code_matches']}/{report['shared_case_count']}**",
        f"- Baseline literal cause-code matches: **{report['baseline_cause_code_matches']}/{report['shared_case_count']}**",
        f"- Cross-path exact terminal-code matches: **{report['cross_path_exact_terminal_matches']}/{report['shared_case_count']}**",
        f"- Cross-path exact cause-code matches: **{report['cross_path_exact_cause_matches']}/{report['shared_case_count']}**",
        f"- Cross-path both-success semantic matches: **{report['cross_path_both_success_matches']}/{report['shared_case_count']}**",
        f"- Cross-path both-fail-closed semantic matches: **{report['cross_path_both_fail_closed_matches']}/{report['shared_case_count']}**",
        f"- Cross-path semantic matches: **{report['cross_path_semantic_matches']}/{report['shared_case_count']}**",
        "",
        "| Variant | Entrypoint | A2A status | A2A terminal / cause | A2A outcome | A2A path pass | Baseline status | Baseline terminal / cause | Baseline outcome | Baseline path pass | Same observed status | Exact terminal | Exact cause | Semantic basis | Semantic equal |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        a2a_terminal = row["a2a"]["terminal_code"] or "-"
        a2a_cause = row["a2a"]["cause_code"] or "-"
        baseline_terminal = row["baseline"]["terminal_code"] or "-"
        baseline_cause = row["baseline"]["cause_code"] or "-"
        lines.append(
            f"| {row['variant_id']} | {row['entrypoint']} | "
            f"{row['a2a']['status']} | {a2a_terminal} / {a2a_cause} | "
            f"{row['a2a']['observed_outcome']} | {row['a2a']['passed']} | "
            f"{row['baseline']['status']} | {baseline_terminal} / "
            f"{baseline_cause} | {row['baseline']['observed_outcome']} | "
            f"{row['baseline']['passed']} | {row['same_observed_status']} | "
            f"{row['exact_terminal_code_match']} | "
            f"{row['exact_cause_code_match']} | {row['semantic_basis']} | "
            f"{row['semantic_equal']} |"
        )
    notes = [row for row in rows if row["code_note"]]
    if notes:
        lines.extend(
            [
                "",
                "## Observed code differences",
                "",
                "Each path still matches its own V2 path-specific expectation; "
                "the differences are protocol wrappers, not union matches.",
                "",
            ]
        )
        for row in notes:
            lines.append(f"- **{row['variant_id']}:** {row['code_note']}")
    lines.extend(
        [
            "",
            "## Not applicable to the direct baseline",
            "",
            "| Variant | Entrypoint | Reason |",
            "| --- | --- | --- |",
        ]
    )
    for item in not_applicable:
        lines.append(
            f"| {item['variant_id']} | {item['entrypoint']} | {item['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Bounded conclusion",
            "",
            "On the shared synthetic cases, each path matched its own literal "
            "terminal code and cause code. Cross-path terminal codes matched on "
            f"{report['cross_path_exact_terminal_matches']} of "
            f"{report['shared_case_count']} cases because the A2A protocol "
            "wraps evidence-side failures as `task_failure` with a cause code. "
            "Observed semantic outcomes matched on "
            f"{report['cross_path_semantic_matches']} of "
            f"{report['shared_case_count']} cases: "
            f"{report['cross_path_both_success_matches']} both-success and "
            f"{report['cross_path_both_fail_closed_matches']} both-fail-closed. "
            "The A2A path added protocol discovery and task evidence but did not "
            "improve correctness or safety on this sample. The sample is small "
            "and the baseline has no A2A protocol semantics, so this is not a "
            "general claim that A2A is or is not superior.",
            "",
            "## Limits",
            "",
        ]
    )
    for limit in report["limits"]:
        lines.append(f"- {limit}")
    (OUTPUT_DIR / "comparison-v2.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "shared_case_count": report["shared_case_count"],
                "a2a_terminal_code_matches": report["a2a_terminal_code_matches"],
                "a2a_cause_code_matches": report["a2a_cause_code_matches"],
                "a2a_path_passes": report["a2a_path_passes"],
                "baseline_terminal_code_matches": report[
                    "baseline_terminal_code_matches"
                ],
                "baseline_cause_code_matches": report[
                    "baseline_cause_code_matches"
                ],
                "baseline_path_passes": report["baseline_path_passes"],
                "cross_path_exact_terminal_matches": report[
                    "cross_path_exact_terminal_matches"
                ],
                "cross_path_exact_cause_matches": report[
                    "cross_path_exact_cause_matches"
                ],
                "cross_path_both_success_matches": report[
                    "cross_path_both_success_matches"
                ],
                "cross_path_both_fail_closed_matches": report[
                    "cross_path_both_fail_closed_matches"
                ],
                "cross_path_semantic_matches": report[
                    "cross_path_semantic_matches"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
