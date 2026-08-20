"""Audit the accepted mistake → undo → corrected-reward sequence at 40–42."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .results import PublishedResult
from .scoring import score_prediction


def audit_correction_sequence(
    *,
    competition: str,
    manifests: Mapping[int, dict[str, Any]],
    published: Mapping[str, PublishedResult],
    predictions: Mapping[str, Mapping[str, Decimal]],
    submission_statuses: Mapping[str, str],
    realized_returns: Mapping[str, Decimal],
) -> dict[str, Any]:
    """Verify exact reversal at 41 and corrected 30-symbol settlement at 42."""

    participants = {
        challenge: {
            row["address"]: row
            for row in manifests[challenge]["competitions"][competition][
                "participants"
            ]
        }
        for challenge in (40, 41, 42)
    }
    addresses = sorted(
        set(participants[40])
        | set(participants[41])
        | set(participants[42])
        | set(published)
    )
    comparisons = []
    for address in addresses:
        row40 = participants[40].get(address)
        row41 = participants[41].get(address)
        row42 = participants[42].get(address)
        result = published.get(address)
        reward40 = _net_reward(row40)
        reward41 = _net_reward(row41)
        reward42 = _net_reward(row42)
        undo_delta = reward40 + reward41

        prediction = predictions.get(address)
        if prediction is None:
            computed_gain = Decimal(0)
            computed_reward = Decimal(0)
        else:
            if row40 is None:
                raise ValueError(f"corrected submitter is absent from challenge 40: {address}")
            computed_gain, computed_reward = score_prediction(
                competition,
                prediction,
                realized_returns,
                Decimal(row40["historical_stake"]["decimal"]),
            )
        published_gain = result.relative_gain if result is not None else None
        published_reward = result.wallet_reward if result is not None else None
        original_stake = (
            Decimal(row40["historical_stake"]["decimal"])
            if row40 is not None
            else None
        )
        correction_stake = (
            Decimal(row42["historical_stake"]["decimal"])
            if row42 is not None
            else None
        )
        result_stake = result.stake if result is not None else None
        comparisons.append(
            {
                "address": address,
                "challenge_40_net_reward": str(reward40),
                "challenge_41_undo_reward": str(reward41),
                "undo_delta": str(undo_delta),
                "undo_matches": undo_delta == 0,
                "submission_status": submission_statuses.get(
                    address, "no-submission"
                ),
                "computed_corrected_relative_gain": str(computed_gain),
                "published_corrected_relative_gain": (
                    str(published_gain) if published_gain is not None else None
                ),
                "corrected_relative_gain_matches": computed_gain == published_gain,
                "computed_corrected_wallet_reward": str(computed_reward),
                "published_corrected_wallet_reward": (
                    str(published_reward) if published_reward is not None else None
                ),
                "corrected_wallet_reward_matches": computed_reward
                == published_reward,
                "challenge_42_chain_net_reward": str(reward42),
                "corrected_reward_matches_chain": published_reward == reward42,
                "original_challenge_40_stake": (
                    str(original_stake) if original_stake is not None else None
                ),
                "published_result_stake": (
                    str(result_stake) if result_stake is not None else None
                ),
                "result_stake_matches_original": result_stake == original_stake,
                "challenge_42_historical_stake": (
                    str(correction_stake) if correction_stake is not None else None
                ),
                "challenge_42_stake_delta_from_original": (
                    str(correction_stake - original_stake)
                    if correction_stake is not None and original_stake is not None
                    else None
                ),
            }
        )

    undo_mismatches = [row for row in comparisons if not row["undo_matches"]]
    corrected_mismatches = [
        row
        for row in comparisons
        if not row["corrected_relative_gain_matches"]
        or not row["corrected_wallet_reward_matches"]
        or not row["corrected_reward_matches_chain"]
        or not row["result_stake_matches_original"]
    ]
    return {
        "schema_version": 1,
        "sequence": [40, 41, 42],
        "competition": competition,
        "treatment": "mistake-undo-corrected-settlement",
        "original_submission_challenge": 40,
        "undo_challenge": 41,
        "corrected_settlement_challenge": 42,
        "published_result_embedded_challenge": 40,
        "comparison_count": len(comparisons),
        "undo_mismatch_count": len(undo_mismatches),
        "corrected_mismatch_count": len(corrected_mismatches),
        "challenge_42_stake_change_count": sum(
            row["challenge_42_stake_delta_from_original"] not in (None, "0.000000", "0")
            for row in comparisons
        ),
        "passed": not undo_mismatches and not corrected_mismatches,
        "comparisons": comparisons,
    }


def _net_reward(participant: dict[str, Any] | None) -> Decimal:
    if participant is None:
        return Decimal(0)
    return Decimal(participant["challenge_reward"]["decimal"]) - Decimal(
        participant["burned"]["decimal"]
    )
