"""Evidence-backed production exceptions recovered from published outcomes."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping


CHALLENGE_113_PROBLEM_ID = (
    "challenge-113-hai-target-override-and-stale-updown-result"
)
STALE_RESULT_CIDS = {
    (110, "UPDOWN"): "QmYuTvKSdD7k5A8UNM75HDume1o17BeQ5VL97CP56bitsX",
    (113, "UPDOWN"): "QmWXyyvUsNw5XfDbzknq7knGUsNohPMABqB5crNwRirskY",
    (116, "UPDOWN"): "QmQFS2AEcbmGCWvJSvi78neiLCCaCgfxuMSFAUNx6YUwuQ",
    (117, "NEUTRAL"): "QmQW16CZjTTL25jpPkA4B4y9jF9UxNL4gpF4r5xscZcDeT",
    (117, "UPDOWN"): "QmSBwXPHHSQcVjR8ZuqxuXvWqBadQgGEQfUbZm3YVSpkj4",
}

# Backward-compatible public view used by existing evidence/tests.
STALE_UPDOWN_RESULT_CIDS = {
    challenge: cid
    for (challenge, competition), cid in STALE_RESULT_CIDS.items()
    if competition == "UPDOWN"
}

RECOVERED_LATE_RESULT_REFERENCES = {
    (116, "UPDOWN"): {
        "cid": "QmSBwXPHHSQcVjR8ZuqxuXvWqBadQgGEQfUbZm3YVSpkj4",
        "sha256": "bbf1e4683be3325628969da4638f9c0cdaf04c8eca9a33f7c08f4985d9107951",
        "published_under_challenge": 117,
    }
}


def is_invalid_zero_financial_result_omission(
    *, submission_status: str, stake: Decimal, chain_reward: Decimal
) -> bool:
    """Return whether an omitted row cannot carry a score or wallet outcome."""

    return (
        submission_status in {"invalid", "unavailable", "no-submission"}
        and stake == 0
        and chain_reward == 0
    )


def apply_realized_return_overrides(
    challenge: int,
    realized_returns: Mapping[str, Decimal],
) -> tuple[dict[str, Decimal], list[dict[str, str]]]:
    """Apply only production overrides proven by exact historical reproduction."""

    values = dict(realized_returns)
    if challenge != 113:
        return values, []
    if "HAI" not in values:
        raise ValueError("challenge 113 realized returns lack HAI")

    dataset_value = values["HAI"]
    values["HAI"] = Decimal(1)
    return values, [
        {
            "symbol": "HAI",
            "loaded_dataset_value": str(dataset_value),
            "production_value": "1",
            "problem_id": CHALLENGE_113_PROBLEM_ID,
            "basis": (
                "the unique full-rank return vector inferred from 44 published "
                "NEUTRAL gains and 42 on-chain UPDOWN rewards"
            ),
        }
    ]
