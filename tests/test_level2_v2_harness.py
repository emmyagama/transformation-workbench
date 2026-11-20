"""Guards for the V2 Level 2 harness and its frozen artifacts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tests.evaluation.level2_v2_common import (
    PACK_DIR,
    SHARED_CASES,
    load_corpus,
    validate_corpus_routing,
    variant_by_id,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence" / "level-2"


def test_v2_corpus_labels_paths_and_shared_cases() -> None:
    corpus = load_corpus()
    validate_corpus_routing(corpus)
    assert len(corpus["cases"]) == 10
    assert sum(len(case["variants"]) for case in corpus["cases"]) == 24
    for case in corpus["cases"]:
        for variant in case["variants"]:
            assert variant["expected"]["path"] == case["entrypoint"]
            if variant["variant_id"] in SHARED_CASES:
                assert variant["baseline_expected"]["path"] == "baseline"
            else:
                assert "baseline_expected" not in variant


def test_v2_l2_04b_is_path_specific() -> None:
    corpus = load_corpus()
    variant = variant_by_id(corpus, "L2-04b")
    assert variant["expected"]["error_code"] == "task_failure"
    assert variant["expected"]["cause_code"] == "request_mismatch"
    assert variant["baseline_expected"]["error_code"] == "request_mismatch"
    assert variant["baseline_expected"]["cause_code"] is None


def test_v2_rejects_label_and_runner_mismatch() -> None:
    corpus = load_corpus()
    mutated = copy.deepcopy(corpus)
    variant = mutated["cases"][0]["variants"][0]
    variant["expected"]["path"] = "coordinator"
    with pytest.raises(ValueError, match="expected path"):
        validate_corpus_routing(mutated)


def test_v2_scorecard_scored_every_declared_invariant() -> None:
    report = json.loads(
        (EVIDENCE / "scorecard-v2.json").read_text(encoding="utf-8")
    )
    thresholds = json.loads(
        (PACK_DIR / "thresholds-v2.json").read_text(encoding="utf-8")
    )
    assert report["variant_count"] == 24
    assert report["passed"] == 24
    assert report["missed"] == 0
    assert report["terminal_code_matches"] == 24
    assert report["cause_code_matches"] == 24
    assert report["all_declared_invariants_scored"] is True
    assert report["workflow_variant_count"] == 15
    assert report["coordinator_variant_count"] == 9
    for row in report["rows"]:
        for field in thresholds["record_fields"]:
            assert field in row, (row["variant_id"], field)
        assert row["entrypoint"] == row["runner_entrypoint"]
        assert row["expected"]["status"] in {"complete", "failure", "refused"}
        assert row["observed_outcome"] in {
            "success",
            "fail_closed",
            "indeterminate",
        }
        assert row["attempt_count"] == row["retry_count"] + 1 or (
            row["attempt_count"] == 0 and row["retry_count"] == 0
        )
        assert row["retry_count"] <= row["max_retries"]
        assert row["attempt_count"] <= row["max_retries"] + 1
        assert set(row["expected"]["invariants"]) <= set(row["dimensions"])
        assert row["passed"] is all(row["dimensions"].values())
        assert row["sanitized_trace"] or row["evidence_pointer"]
    by_id = {row["variant_id"]: row for row in report["rows"]}
    assert by_id["L2-05b"]["failure_category"] == "intake_validation"
    assert by_id["L2-08c"]["attempt_count"] == 2
    assert by_id["L2-08c"]["retry_count"] == 1
    assert by_id["L2-08c"]["max_retries"] == 1
    assert by_id["L2-09a"]["trace_reproducibility"] == "timing_dependent"
    assert by_id["L2-09b"]["trace_reproducibility"] == "timing_dependent"
    assert "trace_reproducibility" not in by_id["L2-01a"]


def test_v2_comparison_separates_codes_and_semantics() -> None:
    report = json.loads(
        (EVIDENCE / "comparison-v2.json").read_text(encoding="utf-8")
    )
    assert report["shared_case_count"] == 13
    assert report["a2a_terminal_code_matches"] == 13
    assert report["a2a_cause_code_matches"] == 13
    assert report["a2a_path_passes"] == 13
    assert report["baseline_terminal_code_matches"] == 13
    assert report["baseline_cause_code_matches"] == 13
    assert report["baseline_path_passes"] == 13
    assert report["cross_path_exact_terminal_matches"] == 10
    assert report["cross_path_exact_cause_matches"] == 10
    assert report["cross_path_both_success_matches"] == 1
    assert report["cross_path_both_fail_closed_matches"] == 12
    assert report["cross_path_semantic_matches"] == 13
    assert "observed outcomes only" in report["semantic_definition"]
    assert report["matching_policy"] == (
        "literal_path_specific_terminal_and_cause_no_union"
    )
    for row in report["rows"]:
        assert row["same_observed_status"] in {True, False}
        assert row["both_complete_with_successful_result"] is (
            row["a2a"]["observed_outcome"] == "success"
            and row["baseline"]["observed_outcome"] == "success"
        )
        assert row["both_fail_closed"] is (
            row["a2a"]["observed_outcome"] == "fail_closed"
            and row["baseline"]["observed_outcome"] == "fail_closed"
        )
        assert row["semantic_equal"] is (
            row["same_observed_status"]
            and (
                row["both_complete_with_successful_result"]
                or row["both_fail_closed"]
            )
        )
