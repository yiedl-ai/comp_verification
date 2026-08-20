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
