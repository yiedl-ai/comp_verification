"""Evidence-backed production exceptions recovered from published outcomes."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping


CHALLENGE_113_PROBLEM_ID = (
    "challenge-113-hai-target-override-and-stale-updown-result"
)
STALE_UPDOWN_RESULT_CIDS = {
    110: "QmYuTvKSdD7k5A8UNM75HDume1o17BeQ5VL97CP56bitsX",
    113: "QmWXyyvUsNw5XfDbzknq7knGUsNohPMABqB5crNwRirskY",
    116: "QmQFS2AEcbmGCWvJSvi78neiLCCaCgfxuMSFAUNx6YUwuQ",
}


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
