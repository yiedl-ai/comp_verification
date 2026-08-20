from decimal import Decimal

from comp_verification.correction_40_42 import audit_correction_sequence
from comp_verification.results import PublishedResult


def _manifest(challenge: int, reward: str, burn: str, stake: str = "10") -> dict:
    return {
        "challenge": challenge,
        "competitions": {
            "UPDOWN": {
                "participants": [{
                    "address": "0x0000000000000000000000000000000000000001",
                    "historical_stake": {"decimal": stake},
                    "challenge_reward": {"decimal": reward},
                    "burned": {"decimal": burn},
                }]
            }
        },
    }


def test_mistake_undo_and_corrected_settlement_are_one_audit() -> None:
    address = "0x0000000000000000000000000000000000000001"
    published = PublishedResult(
        address=address,
        competition="UPDOWN",
        challenge=40,
        relative_gain=Decimal("0.2"),
        wallet_reward=Decimal("2.000000"),
        stake=Decimal("10"),
    )
    report = audit_correction_sequence(
        competition="UPDOWN",
        manifests={
            40: _manifest(40, "1", "0"),
            41: _manifest(41, "0", "1"),
            42: _manifest(42, "2", "0", stake="11"),
        },
        published={address: published},
        predictions={address: {"BTC": Decimal("1")}},
        submission_statuses={address: "valid"},
        realized_returns={"BTC": Decimal("0.2")},
    )

    assert report["passed"] is True
    assert report["undo_mismatch_count"] == 0
    assert report["corrected_mismatch_count"] == 0
    assert report["challenge_42_stake_change_count"] == 1
