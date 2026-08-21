from pathlib import Path

import pytest

from comp_verification.corrections import load_verified_result_correction


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "0xC8519524013348466e18fC1747d11F1feA9473fd"
UPDOWN_CONTRACT = "0xEcB9716867f9300F2706EdbB5b81c7a0AbDC5B29"
VALUE_14 = 7894658387054752303893393541241638517829921050117961214291617257572895210842
VALUE_28 = 73398202505894642167321220588351812944232277344721481762540011419834359901777
VALUE_110 = 17144695397693531176695772460502920802250530955906386517960857332793847214977
VALUE_113 = 46015637770058373047585978234480914682119304915201755113090096508719973870538
VALUE_116 = 25872883947787244428569787043179676246743533514850368395414395112635834716859
VALUE_117_NEUTRAL = 57338318781402924606160931069063199383675333713051285855330374941836454043773
VALUE_117_UPDOWN = 111217540323611032783770449101173250929819138932913901853961095197705014877194
VALUE_123 = 26488423380841783425473974302955525120295499947912071568755599923269140444906
VALUE_134 = 88158303964372024732795351759045982160813748605270853982642934349785080675960


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


def test_challenge_113_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE_113)

    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=113,
        competition="UPDOWN",
        contract=UPDOWN_CONTRACT,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == (
        "QmVBn6G4hsQQPDiGtxK4t7sqr1kTt4svJfVE8HCqfjDkgh"
    )
    assert rpc.blocks == [hex(92388399)]


def test_challenge_116_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE_116)

    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=116,
        competition="UPDOWN",
        contract=UPDOWN_CONTRACT,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == (
        "QmSBwXPHHSQcVjR8ZuqxuXvWqBadQgGEQfUbZm3YVSpkj4"
    )
    assert rpc.blocks == [hex(92387928)]


@pytest.mark.parametrize(
    ("competition", "contract", "value", "cid", "block"),
    [
        (
            "NEUTRAL",
            CONTRACT,
            VALUE_117_NEUTRAL,
            "QmWsViqPqioAocK6BZEoy5tAwrFLcJ6MhGHEZRTo2x9t3E",
            92387854,
        ),
        (
            "UPDOWN",
            UPDOWN_CONTRACT,
            VALUE_117_UPDOWN,
            "QmetVGHijZuU1dE7DFoAtKA2o2miV4rXuJQNakNVheJrp9",
            92387823,
        ),
    ],
)
def test_challenge_117_corrections_are_verified_at_pinned_blocks(
    competition: str, contract: str, value: int, cid: str, block: int
) -> None:
    rpc = CorrectionRpc(value)
    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=117,
        competition=competition,
        contract=contract,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == cid
    assert rpc.blocks == [hex(block)]


def test_challenge_123_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE_123)

    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=123,
        competition="UPDOWN",
        contract=UPDOWN_CONTRACT,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == (
        "QmSHFdrvv1tc1k3tNPsdi16R3yZCxJBN6SgQWNVigmTCDw"
    )
    assert rpc.blocks == [hex(92387180)]


def test_challenge_134_correction_is_verified_at_pinned_block() -> None:
    rpc = CorrectionRpc(VALUE_134)

    correction = load_verified_result_correction(
        ROOT,
        rpc,  # type: ignore[arg-type]
        challenge=134,
        competition="UPDOWN",
        contract=UPDOWN_CONTRACT,
    )

    assert correction is not None
    assert correction["corrected_content"]["cid"] == (
        "QmbTUqSybK6C9MvfQB1aZXJ3KPxvGDWYpzAjbbweGM3MR9"
    )
    assert rpc.blocks == [hex(92387013)]


def test_result_correction_rejects_a_different_on_chain_value() -> None:
    with pytest.raises(ValueError, match="on-chain correction differs"):
        load_verified_result_correction(
            ROOT,
            CorrectionRpc(VALUE_14 + 1),  # type: ignore[arg-type]
            challenge=14,
            competition="NEUTRAL",
            contract=CONTRACT,
        )
