from decimal import Decimal

from comp_verification.results import PublishedResult, compare_results_to_chain


def test_compare_positive_reward_and_negative_burn() -> None:
    manifest = {
        "challenge": 1,
        "observed_block": 100,
        "competitions": {
            "UPDOWN": {
                "contract": "0xcontract",
                "content": {"results": {"cid": "QmResults"}},
                "participants": [
                    _participant("0x" + "11" * 20, "10.000000", "1.250000", "0.000000"),
                    _participant("0x" + "22" * 20, "20.000000", "0.000000", "0.500000"),
                ],
            }
        },
    }
    results = {
        "0x" + "11" * 20: _result("0x" + "11" * 20, "10", "1.25"),
        "0x" + "22" * 20: _result("0x" + "22" * 20, "20", "-0.5"),
    }

    report = compare_results_to_chain(manifest, "UPDOWN", results)

    assert report["passed"] is True
    assert report["mismatch_count"] == 0


def _participant(address: str, stake: str, reward: str, burned: str) -> dict:
    return {
        "address": address,
        "historical_stake": {"decimal": stake},
        "challenge_reward": {"decimal": reward},
        "burned": {"decimal": burned},
    }


def _result(address: str, stake: str, reward: str) -> PublishedResult:
    return PublishedResult(
        address=address,
        competition="UPDOWN",
        challenge=1,
        relative_gain=Decimal("0.1"),
        wallet_reward=Decimal(reward),
        stake=Decimal(stake),
    )
