"""Verify explicit on-chain corrections to otherwise immutable result references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .encoding import (
    decode_uint,
    digest_to_cid_v0,
    encode_address,
    encode_call,
    encode_uint,
)
from .rpc import ContractCall, PolygonRpc


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
RESULTS_CID_CORRECTION_ITEM_NUMBER = 0


def load_verified_result_correction(
    root: Path,
    rpc: PolygonRpc,
    *,
    challenge: int,
    competition: str,
    contract: str,
) -> dict[str, Any] | None:
    """Load a tracked correction and prove its value at the pinned Polygon block."""

    path = (
        root
        / "manifests"
        / "corrections"
        / f"challenge-{challenge:03d}-{competition.lower()}.json"
    )
    if not path.exists():
        return None
    correction = json.loads(path.read_text(encoding="utf-8"))
    if correction.get("challenge") != challenge:
        raise ValueError(f"correction challenge differs from context: {path}")
    if correction.get("competition") != competition:
        raise ValueError(f"correction competition differs from context: {path}")
    if correction.get("contract", "").lower() != contract.lower():
        raise ValueError(f"correction contract differs from context: {path}")

    storage = correction["storage"]
    if storage["participant"].lower() != ZERO_ADDRESS:
        raise ValueError(f"correction participant is not the zero address: {path}")
    if storage["item_number"] != RESULTS_CID_CORRECTION_ITEM_NUMBER:
        raise ValueError(f"correction uses an unsupported information item: {path}")
    call = ContractCall(
        to=contract,
        data=encode_call(
            "getInformation(uint32,address,uint256)",
            encode_uint(challenge),
            encode_address(ZERO_ADDRESS),
            encode_uint(RESULTS_CID_CORRECTION_ITEM_NUMBER),
        ),
    )
    observed_value = decode_uint(
        rpc.call(call, block=hex(correction["observation"]["block_number"]))
    )
    expected_value = int(storage["value_uint"])
    if observed_value != expected_value:
        raise ValueError(f"on-chain correction differs from tracked evidence: {path}")
    digest = "0x" + observed_value.to_bytes(32, "big").hex()
    cid = digest_to_cid_v0(digest)
    content = correction["corrected_content"]
    if digest != content["digest"] or cid != content["cid"]:
        raise ValueError(f"correction CID/digest conversion differs: {path}")
    return correction
