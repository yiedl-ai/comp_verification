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


def test_register_captures_open_challenge_nineteen_mismatches() -> None:
    problem = load_problem_register().by_id(
        "challenge-19-three-addresses-zeroed-in-both-competitions"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 6
    assert len(problem.raw["details"]["submissions"]) == 6
    assert problem.scope.challenges == frozenset({19})


def test_register_captures_challenge_twenty_eight_bad_result_reference() -> None:
    problem = load_problem_register().by_id(
        "challenge-28-neutral-results-cid-is-challenge-29-public-key"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.scope.audit_kinds == frozenset({"publication", "scoring"})
    assert problem.raw["details"]["result_reference"]["size"] == 450


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

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 1
    assert problem.raw["details"]["submission"]["cid"] == (
        "QmXFWqVuLEvqRwtv7RQyczJRHGWQ8agzCejXpRVmE2mmgK"
    )
    assert problem.raw["details"]["submission_close"][
        "seconds_after_submission"
    ] == 24422


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


def test_register_captures_challenge_113_recovered_override_and_stale_result() -> None:
    problem = load_problem_register().by_id(
        "challenge-113-hai-target-override-and-stale-updown-result"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.raw["details"]["production_override"] == {
        "evidence": (
            "Replacing only HAI target_updown with exactly 1 reproduces all "
            "available challenge-113 scores and rewards with the historical "
            "scorer and numeric path."
        ),
        "symbol": "HAI",
        "value": "1",
    }
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 112


def test_register_captures_challenge_110_stale_updown_result() -> None:
    problem = load_problem_register().by_id(
        "challenge-110-stale-updown-result-reference"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "updown_exact_on_chain_reward_count"
    ] == 38
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 109


def test_register_captures_challenge_116_stale_updown_result() -> None:
    problem = load_problem_register().by_id(
        "challenge-116-stale-updown-result-reference"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "updown_exact_on_chain_reward_count"
    ] == 38
    assert problem.raw["details"]["recovered_updown_result"][
        "challenge_116_relative_gain_mismatches"
    ] == 0
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 115


def test_register_captures_challenge_117_late_result_references() -> None:
    problem = load_problem_register().by_id(
        "challenge-117-one-challenge-late-result-references"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.scope.competitions == frozenset({"NEUTRAL", "UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "neutral_exact_on_chain_reward_count"
    ] == 54
    assert problem.raw["details"]["stale_results"]["UPDOWN"][
        "challenge_116_relative_gain_mismatches"
    ] == 0


def test_register_captures_challenge_129_zero_financial_omissions() -> None:
    problem = load_problem_register().by_id(
        "challenge-129-invalid-zero-financial-result-row-omissions"
    )

    assert problem.status == "documented"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 4
    assert problem.raw["details"]["scoring_reproduction"] == {
        "neutral_exact_valid_count": 51,
        "neutral_mismatch_count": 0,
        "updown_exact_valid_count": 38,
        "updown_mismatch_count": 0,
    }


def test_register_captures_challenge_134_stale_updown_result() -> None:
    problem = load_problem_register().by_id(
        "challenge-134-stale-updown-result-reference"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"] == {
        "neutral_exact_reward_count": 53,
        "neutral_exact_score_count": 53,
        "updown_exact_on_chain_reward_count": 39,
        "updown_score_status": "unverifiable-because-result-file-is-stale",
    }
    assert problem.raw["details"]["stale_updown_result"][
        "stake_reward_burn_field_mismatches_against_challenge_134_chain"
    ] == 78
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 133


def test_register_captures_challenge_123_stale_updown_result() -> None:
    problem = load_problem_register().by_id(
        "challenge-123-stale-updown-result-reference"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.scope.competitions == frozenset({"UPDOWN"})
    assert problem.raw["details"]["reproduction"][
        "updown_exact_on_chain_reward_count"
    ] == 37
    assert problem.raw["details"]["stale_updown_result"][
        "stake_reward_burn_field_mismatches_against_challenge_123_chain"
    ] == 88
    assert problem.raw["details"]["stale_updown_result"]["same_as_challenge"] == 122


def test_register_captures_valid_zero_financial_result_omissions() -> None:
    problem = load_problem_register().by_id(
        "challenges-142-and-154-161-valid-zero-financial-result-row-omissions"
    )

    assert problem.status == "open"
    assert problem.counts_as_pass is False
    assert problem.raw["affected_comparisons"] == 9
    assert problem.scope.challenges == frozenset(
        {142, 154, 155, 156, 157, 158, 159, 160, 161}
    )
    assert problem.raw["details"]["verified_scoring_example"] == {
        "challenge": 154,
        "computed_relative_gain": "0.0002248414479546002094773049480",
        "computed_wallet_reward": "0.000000",
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
