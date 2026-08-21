import json
from pathlib import Path

import pytest

from comp_verification.problem_register import (
    DEFAULT_REGISTER_PATH,
    ProblemRegisterError,
    load_problem_register,
)


ADDRESS = "0x8a8e1c4e454e092fc19c6cca2034bd22b29781e7"
PROBLEM_ID = "challenge-8-late-submission-rpc-sync-and-ipfs-availability"


def test_canonical_register_captures_challenge_eight_evidence() -> None:
    register = load_problem_register()
    problem = register.by_id(PROBLEM_ID)

    assert problem.headline == (
        "Challenge 8: Late submissions likely omitted by an early or stale "
        "backend snapshot"
    )
    assert problem.status == "accepted"
    assert problem.audit_treatment["changes_outcome"] is True
    assert problem.audit_treatment["mode"] == "accepted-historical-exception"
    assert problem.counts_as_pass is True
    assert problem.scope.challenges == frozenset({8})
    assert len(problem.raw["details"]["submissions"]) == 2
    assert {
        row["competition"]: row["cid"]
        for row in problem.raw["details"]["submissions"]
    } == {
        "NEUTRAL": "QmckC49ng6oBt3Bbsg8Q2HYefBq41ri1H3x3pXjUzLuVcm",
        "UPDOWN": "QmWDDvp3H38SgKPX7RNfhDQy16VT9tpqjqaFafpeAYhQCX",
    }


def test_register_matches_general_audit_contexts() -> None:
    register = load_problem_register()

    assert [item.id for item in register.find(challenge=8)] == [PROBLEM_ID]
    assert [
        item.id
        for item in register.find(
            challenge=8,
            competition="neutral",
            audit_kind="SCORING",
            address=ADDRESS.upper(),
        )
    ] == [PROBLEM_ID]
    assert register.find(challenge=7) == ()
    assert register.find(challenge=8, audit_kind="publication") == ()
    assert register.find(challenge=8, address="0x0000000000000000000000000000000000000000") == ()


def test_register_captures_challenge_fourteen_broken_result_reference() -> None:
    problem = load_problem_register().by_id(
        "challenge-14-neutral-results-cid-is-dataset-15"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.scope.audit_kinds == frozenset({"publication", "scoring"})
    assert problem.raw["details"]["same_as_dataset_challenge"] == 15
    assert problem.raw["details"]["correction"]["information_item_number"] == 0


def test_register_captures_accepted_challenge_nineteen_snapshot_omissions() -> None:
    problem = load_problem_register().by_id(
        "challenge-19-three-addresses-zeroed-in-both-competitions"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.raw["affected_comparisons"] == 6
    assert len(problem.raw["details"]["submissions"]) == 6
    assert problem.raw["details"]["conclusion"] == (
        "The scoring input snapshot omitted the final three submitters in both "
        "competitions, causing the published zero scores and rewards."
    )
    assert problem.scope.challenges == frozenset({19})


def test_register_captures_accepted_challenge_twenty_eight_correction() -> None:
    problem = load_problem_register().by_id(
        "challenge-28-neutral-results-cid-is-challenge-29-public-key"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.scope.audit_kinds == frozenset({"publication", "scoring"})
    assert problem.raw["details"]["result_reference"]["size"] == 450
    assert problem.raw["details"]["correction"]["information_item_number"] == 0


def test_register_captures_accepted_challenge_thirty_three_snapshot_omission() -> None:
    problem = load_problem_register().by_id(
        "challenge-33-neutral-last-submission-published-as-zero"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.raw["details"]["scoring_database"]["submission_rows"] == 0
    assert problem.raw["details"]["conclusion"] == (
        "The scoring input snapshot omitted the final valid NEUTRAL submission, "
        "causing its published zero score and reward."
    )


def test_register_captures_challenge_fifty_two_recovered_policy_boundary() -> None:
    problem = load_problem_register().by_id(
        "challenge-52-production-only-77-symbol-policy-cutover"
    )

    assert problem.status == "documented"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 0
    assert problem.raw["details"]["policy_transition"] == {
        "last_verified_30_symbol_challenge": 51,
        "first_verified_77_symbol_challenge": 52,
        "recovered_policy": "legacy-static-77-v1",
    }


def test_register_captures_challenge_seventy_three_zeroed_submission() -> None:
    problem = load_problem_register().by_id(
        "challenge-73-neutral-valid-submission-published-as-zero"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.raw["affected_comparisons"] == 1
    assert problem.raw["details"]["submission"]["cid"] == (
        "QmXFWqVuLEvqRwtv7RQyczJRHGWQ8agzCejXpRVmE2mmgK"
    )
    assert problem.raw["details"]["submission_close"][
        "seconds_after_submission"
    ] == 24422
    assert problem.raw["details"]["scoring_database"]["submission_rows"] == 0
    assert problem.raw["details"]["blank_symbol_evidence"] == {
        "accepted_nonzero_submissions_checked": 61,
        "accepted_with_blank_symbol_rows": 0,
        "affected_blank_prediction": "0.53340846",
        "affected_blank_row_index_after_header": 1556,
        "affected_blank_symbol_rows": 1,
        "required_asset_count": 77,
        "required_duplicate_count": 0,
        "required_missing_count": 0,
        "required_non_numeric_count": 0,
    }


def test_register_captures_challenge_ninety_five_unavailable_submission() -> None:
    problem = load_problem_register().by_id(
        "challenge-95-neutral-malformed-unavailable-submission-reference"
    )

    assert problem.status == "documented"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 0
    assert problem.raw["details"]["submission"]["digest_ascii"] == (
        "cb1fdc7e38400f7966307a2ee1f4a2d0"
    )


def test_register_captures_challenge_ninety_four_unavailable_submission() -> None:
    problem = load_problem_register().by_id(
        "challenge-94-updown-malformed-unavailable-submission-reference"
    )

    assert problem.status == "documented"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 0
    assert problem.raw["details"]["submission"]["digest_ascii"] == (
        "d0f19a0e4412dfa347605f8cff5c57c5"
    )
    assert problem.scope.competitions == frozenset({"UPDOWN"})


def test_register_captures_accepted_challenge_113_cap_and_correction() -> None:
    problem = load_problem_register().by_id(
        "challenge-113-hai-target-override-and-stale-updown-result"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    override = problem.raw["details"]["production_override"]
    assert override["symbol"] == "HAI"
    assert override["value"] == "1"
    assert "sum of absolute portfolio weights equals 1" in override[
        "portfolio_margin_rule"
    ]
    assert "allocated to HAI" in override["rationale"]
    assert problem.raw["details"]["correction"]["information_item_number"] == 0
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 112


def test_register_captures_accepted_challenge_110_correction() -> None:
    problem = load_problem_register().by_id(
        "challenge-110-stale-updown-result-reference"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "updown_exact_on_chain_reward_count"
    ] == 38
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 109
    assert problem.raw["details"]["correction"]["information_item_number"] == 0


def test_register_captures_accepted_challenge_116_correction() -> None:
    problem = load_problem_register().by_id(
        "challenge-116-stale-updown-result-reference"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "updown_exact_on_chain_reward_count"
    ] == 38
    assert problem.raw["details"]["recovered_updown_result"][
        "challenge_116_relative_gain_mismatches"
    ] == 0
    assert problem.raw["details"]["correction"]["information_item_number"] == 0
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 115


def test_register_captures_accepted_challenge_117_corrections() -> None:
    problem = load_problem_register().by_id(
        "challenge-117-one-challenge-late-result-references"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.scope.competitions == frozenset({"NEUTRAL", "UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "neutral_exact_on_chain_reward_count"
    ] == 54
    assert problem.raw["details"]["stale_results"]["UPDOWN"][
        "challenge_116_relative_gain_mismatches"
    ] == 0
    assert set(problem.raw["details"]["corrections"]) == {"NEUTRAL", "UPDOWN"}


def test_register_captures_accepted_challenge_129_zero_financial_omissions() -> None:
    problem = load_problem_register().by_id(
        "challenge-129-invalid-zero-financial-result-row-omissions"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.raw["affected_comparisons"] == 4
    assert problem.raw["details"]["scoring_reproduction"] == {
        "neutral_exact_valid_count": 51,
        "neutral_mismatch_count": 0,
        "updown_exact_valid_count": 38,
        "updown_mismatch_count": 0,
    }


def test_register_captures_accepted_challenge_134_correction() -> None:
    problem = load_problem_register().by_id(
        "challenge-134-stale-updown-result-reference"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"] == {
        "neutral_exact_reward_count": 53,
        "neutral_exact_score_count": 53,
        "updown_exact_on_chain_reward_count": 39,
        "updown_exact_published_row_count": 95,
        "updown_score_status": "exact-via-corrected-result-reference",
    }
    assert problem.raw["details"]["stale_updown_result"][
        "stake_reward_burn_field_mismatches_against_challenge_134_chain"
    ] == 78
    assert problem.raw["details"]["correction"]["information_item_number"] == 0
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 133


def test_register_captures_accepted_challenge_123_correction() -> None:
    problem = load_problem_register().by_id(
        "challenge-123-stale-updown-result-reference"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "updown_exact_on_chain_reward_count"
    ] == 37
    assert problem.raw["details"]["stale_updown_result"][
        "stake_reward_burn_field_mismatches_against_challenge_123_chain"
    ] == 88
    assert problem.raw["details"]["correction"]["information_item_number"] == 0
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 122


def test_register_captures_valid_zero_financial_result_omissions() -> None:
    problem = load_problem_register().by_id(
        "challenges-142-and-154-161-valid-zero-financial-result-row-omissions"
    )

    assert problem.status == "accepted"
    assert problem.counts_as_pass is True
    assert problem.raw["affected_comparisons"] == 9
    assert problem.scope.challenges == frozenset(
        {142, 154, 155, 156, 157, 158, 159, 160, 161}
    )
    assert problem.raw["details"]["verified_scoring_example"] == {
        "challenge": 154,
        "computed_relative_gain": "0.0002248414479546002094773049480",
        "computed_wallet_reward": "0.000000",
    }


def test_register_captures_resolved_dataset_168_availability_gap() -> None:
    problem = load_problem_register().by_id(
        "dataset-168-current-ipfs-block-availability-gap"
    )

    assert problem.status == "resolved"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 0
    assert problem.scope.challenges == frozenset({167, 168})
    assert problem.scope.audit_kinds == frozenset({"dataset-ingestion"})
    assert problem.raw["details"]["missing_range"] == {
        "start": 729284608,
        "end_inclusive": 738197503,
    }
    assert problem.raw["details"]["resolution"] == {
        "challenge_167_neutral_exact_comparisons": 122,
        "challenge_167_updown_exact_comparisons": 92,
        "challenge_168_evaluation_fixture_sha256": (
            "ae38f14835aa97b37fcc0d412e2bacff639444880b250344eabcd7e61c3116ee"
        ),
        "challenge_168_neutral_exact_comparisons": 122,
        "challenge_168_updown_exact_comparisons": 92,
        "completed_archive_bytes": 1020812396,
        "completed_archive_sha256": (
            "ee4cf8b4d5179c19ef8a1dc1fb5ca0529d8e55f85b4b634780bb5934fd2cb95f"
        ),
        "completed_via": "authenticated yiedl-temp.mypinata.cloud retry",
        "raw_archive_pruned_after_reverification": True,
        "resolved_on": "2026-08-21",
        "source_cid_verified": True,
        "target_fixture_sha256": (
            "fa350b8a6f4f20ca46fc218cffc61b8f01cf67e223de537e0b63dbe7da07dad4"
        ),
    }


def test_register_captures_challenge_166_unpublished_targets() -> None:
    problem = load_problem_register().by_id(
        "challenge-166-unpublished-old-basket-settlement-targets"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.scope.challenges == frozenset({166})
    assert problem.raw["details"]["recovery_validation"] == {
        "combined_equation_count": 85,
        "combined_matrix_rank": 77,
        "dataset_or_alias_values_matching_recovered_vector": 70,
        "exact_calibration_gain_count": 7,
        "exact_holdout_gain_count": 78,
        "neutral_valid_submission_count": 49,
        "updown_valid_submission_count": 36,
        "wallet_reward_mismatch_count": 0,
    }


def test_report_reference_preserves_existing_report_shape() -> None:
    reference = load_problem_register().by_id(PROBLEM_ID).report_reference()

    assert reference == {
        "id": PROBLEM_ID,
        "document": "docs/caveats.md",
        "anchor": (
            "challenge-8-late-submission-rpc-synchronization-and-ipfs-availability"
        ),
        "classification": "inferred-operational-exception",
        "counts_as_pass": True,
        "summary": (
            "The early backend likely captured submissions before the final "
            "on-chain close state, read from a lagging RPC, or encountered late "
            "IPFS availability; the two raw mismatches are accepted as caveated "
            "historical exceptions."
        ),
    }


def test_register_rejects_duplicate_ids(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_REGISTER_PATH.read_text(encoding="utf-8"))
    payload["problems"].append(payload["problems"][0])
    path = tmp_path / "register.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProblemRegisterError, match="problem ids must be unique"):
        load_problem_register(path)


def test_register_rejects_an_accepted_status_without_outcome_change(
    tmp_path: Path,
) -> None:
    payload = json.loads(DEFAULT_REGISTER_PATH.read_text(encoding="utf-8"))
    payload["problems"][0]["audit_treatment"]["changes_outcome"] = False
    path = tmp_path / "register.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ProblemRegisterError,
        match="accepted status and changes_outcome must agree",
    ):
        load_problem_register(path)
