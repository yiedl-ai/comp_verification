from decimal import Decimal

from comp_verification.historical_exceptions import (
    CHALLENGE_113_PROBLEM_ID,
    CHALLENGE_166_PROBLEM_ID,
    CHALLENGE_166_REALIZED_RETURN_OVERRIDES,
    RECOVERED_LATE_RESULT_REFERENCES,
    STALE_RESULT_CIDS,
    STALE_UPDOWN_RESULT_CIDS,
    apply_realized_return_overrides,
    is_invalid_zero_financial_result_omission,
)
from comp_verification.policies import policy_for_challenge
from comp_verification.workflow import FirstTenWorkflow


def test_only_challenge_113_overrides_hai() -> None:
    source = {"BTC": Decimal("0.1"), "HAI": Decimal("21.227900966966708")}

    ordinary, ordinary_evidence = apply_realized_return_overrides(112, source)
    recovered, evidence = apply_realized_return_overrides(113, source)

    assert ordinary == source
    assert ordinary_evidence == []
    assert recovered == {"BTC": Decimal("0.1"), "HAI": Decimal(1)}
    assert evidence[0]["problem_id"] == CHALLENGE_113_PROBLEM_ID
    assert evidence[0]["production_value"] == "1"
    assert "allocated to HAI" in evidence[0]["rationale"]
    assert source["HAI"] == Decimal("21.227900966966708")


def test_challenge_166_requires_the_exact_recovered_float_values() -> None:
    source = {
        symbol: Decimal(float(literal))
        for symbol, literal in CHALLENGE_166_REALIZED_RETURN_OVERRIDES.items()
    }

    recovered, evidence = apply_realized_return_overrides(166, source)

    assert recovered == source
    assert len(evidence) == 7
    assert {row["problem_id"] for row in evidence} == {CHALLENGE_166_PROBLEM_ID}


def test_challenge_113_updown_fallback_verifies_rewards_but_not_scores(
    tmp_path,
) -> None:
    address = "0x0000000000000000000000000000000000000001"
    workflow = FirstTenWorkflow(root=tmp_path, config=None)  # type: ignore[arg-type]
    observed = {
        "content": {"results": {"cid": STALE_UPDOWN_RESULT_CIDS[113]}},
        "participants": [
            {
                "address": address,
                "submission": {"cid": "QmSubmission"},
                "historical_stake": {"decimal": "10"},
                "challenge_reward": {"decimal": "1.000000"},
                "burned": {"decimal": "0.000000"},
            }
        ],
    }

    report = workflow._stale_result_reward_report(
        challenge=113,
        competition="UPDOWN",
        observed=observed,
        policy=policy_for_challenge(113),
        returns={"BTC": Decimal("0.1")},
        normalized_submissions={address: {"BTC": Decimal(1)}},
        submission_statuses={address: "valid"},
        publication_report={
            "problem": "ValueError: expected challenge 113, found 112",
            "result_bytes_sha256": "digest",
        },
        realized_return_overrides=[],
    )

    assert report["reward_passed"] is True
    assert report["wallet_reward_mismatch_count"] == 0
    assert report["score_comparison_count"] == 0
    assert report["score_passed"] is False
    assert report["passed"] is False


def test_challenge_116_stale_result_is_registered_for_reward_fallback() -> None:
    assert STALE_UPDOWN_RESULT_CIDS[116] == (
        "QmQFS2AEcbmGCWvJSvi78neiLCCaCgfxuMSFAUNx6YUwuQ"
    )


def test_challenge_117_stale_results_are_registered_for_both_competitions() -> None:
    assert STALE_RESULT_CIDS[(117, "NEUTRAL")] == (
        "QmQW16CZjTTL25jpPkA4B4y9jF9UxNL4gpF4r5xscZcDeT"
    )
    assert STALE_RESULT_CIDS[(117, "UPDOWN")] == (
        "QmSBwXPHHSQcVjR8ZuqxuXvWqBadQgGEQfUbZm3YVSpkj4"
    )
    assert RECOVERED_LATE_RESULT_REFERENCES[(116, "UPDOWN")][
        "published_under_challenge"
    ] == 117
    assert STALE_RESULT_CIDS[(134, "UPDOWN")] == (
        "Qmcj37J2B2moDQdxdL648FRqgoS5aravDkmGq4zMX9YuNq"
    )
    assert STALE_RESULT_CIDS[(123, "UPDOWN")] == (
        "QmcxJgkxboo9dNXVEmp6Yds8BNe7uYD3rQodVjxJ8b3LPo"
    )


def test_only_non_scoring_zero_financial_rows_can_be_implicitly_omitted() -> None:
    assert is_invalid_zero_financial_result_omission(
        submission_status="invalid", stake=Decimal(0), chain_reward=Decimal(0)
    )
    assert not is_invalid_zero_financial_result_omission(
        submission_status="valid", stake=Decimal(0), chain_reward=Decimal(0)
    )
    assert not is_invalid_zero_financial_result_omission(
        submission_status="invalid", stake=Decimal(1), chain_reward=Decimal(0)
    )
    assert not is_invalid_zero_financial_result_omission(
        submission_status="invalid", stake=Decimal(0), chain_reward=Decimal(1)
    )
