from pathlib import Path

import pytest

from comp_verification.corrections import load_verified_result_correction


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "0xC8519524013348466e18fC1747d11F1feA9473fd"
UPDOWN_CONTRACT = "0xEcB9716867f9300F2706EdbB5b81c7a0AbDC5B29"
VALUE_14 = 7894658387054752303893393541241638517829921050117961214291617257572895210842
VALUE_28 = 73398202505894642167321220588351812944232277344721481762540011419834359901777
VALUE_110 = 17144695397693531176695772460502920802250530955906386517960857332793847214977


class CorrectionRpc:
    def __init__(self, value: int) -> None:
        self.value = value
        self.blocks: list[str] = []

    def call(self, call: object, block: str = "latest") -> str:
        self.blocks.append(block)
        return "0x" + self.value.to_bytes(32, "big").hex()


def test_canonical_result_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE_14)

    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=14,
        competition="NEUTRAL",
        contract=CONTRACT,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == (
        "QmPWnRa7W3xSVWm2ST5REBiAA8ebbSVdYeFuzSmjGYERzy"
    )
    assert rpc.blocks == [hex(92339630)]


def test_challenge_twenty_eight_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE_28)

    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=28,
        competition="NEUTRAL",
        contract=CONTRACT,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == (
        "QmZG6avbBxpcwN61NcVGggfKEZpjZ6xso5E2joNZ4U97mr"
    )
    assert rpc.blocks == [hex(92383809)]


def test_challenge_110_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE_110)

    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=110,
        competition="UPDOWN",
        contract=UPDOWN_CONTRACT,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == (
        "QmQtcagsLg3m4feM7kphBCyc31DK19qSZFzvDKZa8gAXNG"
    )
    assert rpc.blocks == [hex(92386607)]


def test_result_correction_rejects_a_different_on_chain_value() -> None:
    with pytest.raises(ValueError, match="on-chain correction differs"):
        load_verified_result_correction(
            ROOT,
            CorrectionRpc(VALUE_14 + 1),  # type: ignore[arg-type]
            challenge=14,
            competition="NEUTRAL",
            contract=CONTRACT,
        )
