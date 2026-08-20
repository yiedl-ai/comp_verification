from decimal import Decimal
from pathlib import Path

import pytest

from comp_verification.policies import CHALLENGE_19_CANDIDATE
from comp_verification.submission_fixtures import (
    read_submission_fixture,
    write_submission_fixture,
)


def test_normalized_submission_fixture_round_trip(tmp_path: Path) -> None:
    policy = CHALLENGE_19_CANDIDATE
    address = "0x0000000000000000000000000000000000000001"
    predictions = {
        address: {
            symbol: Decimal(index) / Decimal("10")
            for index, symbol in enumerate(policy.symbols)
        }
    }
    evidence = [
        {
            "address": address,
            "status": "valid",
            "submission_cid": "QmExample",
            "archive_sha256": "a" * 64,
            "predictions_sha256": "b" * 64,
            "prediction_count": len(policy.symbols),
        }
    ]
    destination = tmp_path / "challenge-019-neutral.csv"

    provenance = write_submission_fixture(
        destination,
        challenge=19,
        competition="NEUTRAL",
        policy=policy,
        predictions=predictions,
        participant_evidence=evidence,
    )

    assert provenance["address_count"] == 1
    assert provenance["row_count"] == len(policy.symbols)
    assert read_submission_fixture(destination, policy=policy) == predictions


def test_normalized_submission_fixture_detects_tampering(tmp_path: Path) -> None:
    policy = CHALLENGE_19_CANDIDATE
    address = "0x0000000000000000000000000000000000000001"
    predictions = {address: {symbol: Decimal(1) for symbol in policy.symbols}}
    destination = tmp_path / "challenge-019-neutral.csv"
    write_submission_fixture(
        destination,
        challenge=19,
        competition="NEUTRAL",
        policy=policy,
        predictions=predictions,
        participant_evidence=[
            {
                "address": address,
                "status": "valid",
                "submission_cid": "QmExample",
                "archive_sha256": "a" * 64,
                "predictions_sha256": "b" * 64,
                "prediction_count": len(policy.symbols),
            }
        ],
    )
    destination.write_bytes(destination.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="hash differs"):
        read_submission_fixture(destination, policy=policy)
