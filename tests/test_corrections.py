from pathlib import Path

import pytest

from comp_verification.corrections import load_verified_result_correction


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "0xC8519524013348466e18fC1747d11F1feA9473fd"
VALUE = 7894658387054752303893393541241638517829921050117961214291617257572895210842


class CorrectionRpc:
    def __init__(self, value: int) -> None:
        self.value = value
        self.blocks: list[str] = []

    def call(self, call: object, block: str = "latest") -> str:
        self.blocks.append(block)
        return "0x" + self.value.to_bytes(32, "big").hex()


def test_canonical_result_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE)

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


def test_result_correction_rejects_a_different_on_chain_value() -> None:
    with pytest.raises(ValueError, match="on-chain correction differs"):
        load_verified_result_correction(
            ROOT,
            CorrectionRpc(VALUE + 1),  # type: ignore[arg-type]
            challenge=14,
            competition="NEUTRAL",
            contract=CONTRACT,
        )
