from comp_verification.chain_evidence import _normalize_event
from comp_verification.encoding import event_topic
from comp_verification.summary import _submission_event


def _word(value: int) -> str:
    return f"0x{value:064x}"


def test_normalize_indexed_challenge_event() -> None:
    transaction_hash = "0x" + "ab" * 32
    block_hash = "0x" + "cd" * 32
    log = {
        "topics": [
            event_topic("SubmissionUpdated(uint32,address,bytes32)"),
            _word(7),
            _word(1),
            _word(2),
        ],
        "data": "0x",
        "blockNumber": "0x64",
        "blockHash": block_hash,
        "transactionHash": transaction_hash,
        "transactionIndex": "0x2",
        "logIndex": "0x3",
    }

    event = _normalize_event(log, 7)

    assert event is not None
    assert event["event"] == "SubmissionUpdated"
    assert event["block_number"] == 100
    assert event["transaction_hash"] == transaction_hash
    assert _normalize_event(log, 8) is None


def test_normalize_nonindexed_challenge_event() -> None:
    log = {
        "topics": [event_topic("RewardsPayment(uint32,address,uint256,uint256,uint256)"), _word(1)],
        "data": "0x" + f"{9:064x}" + f"{100:064x}",
        "blockNumber": "0x65",
        "blockHash": "0x" + "12" * 32,
        "transactionHash": "0x" + "34" * 32,
        "transactionIndex": "0x0",
        "logIndex": "0x1",
    }

    event = _normalize_event(log, 9)

    assert event is not None
    assert event["event"] == "RewardsPayment"
    assert _normalize_event(log, 10) is None


def test_find_submission_event_by_topic_address() -> None:
    address = "0x" + "ab" * 20
    event = {
        "event": "SubmissionUpdated",
        "topics": ["0xtopic", _word(8), _word(int(address, 16)), _word(3)],
    }
    manifest = {"competitions": {"UPDOWN": {"events": [event]}}}

    assert _submission_event(manifest, "UPDOWN", address) == event
