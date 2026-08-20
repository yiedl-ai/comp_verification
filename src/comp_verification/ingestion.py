"""Read immutable challenge evidence from the competition contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import CHAIN_ID, CONTRACTS, REGISTRY_ADDRESS, ZERO_BYTES32
from .encoding import decode_bytes32, decode_uint, digest_to_cid_v0
from .jsonio import write_canonical_json
from .rpc import (
    PolygonRpc,
    bytes32_call,
    participant_call,
    read_addresses,
    read_bytes32,
    read_uint,
)

_CONTENT_FIELDS = {
    "dataset": "getDatasetHash(uint32)",
    "public_key": "getKeyHash(uint32)",
    "private_key": "getPrivateKeyHash(uint32)",
    "results": "getResultsHash(uint32)",
}

_PARTICIPANT_FIELDS = {
    "historical_stake": "getStakedAmountForChallenge(uint32,address)",
    "staking_reward": "getStakingRewards(uint32,address)",
    "challenge_reward": "getChallengeRewards(uint32,address)",
    "tournament_reward": "getTournamentRewards(uint32,address)",
    "challenge_score": "getChallengeScores(uint32,address)",
    "tournament_score": "getTournamentScores(uint32,address)",
    "burned": "getBurnedAmount(uint32,address)",
}


def content_reference(digest: str) -> dict[str, str | None]:
    return {"digest": digest, "cid": digest_to_cid_v0(digest)}


def token_amount(raw_value: int) -> dict[str, str]:
    whole, fraction = divmod(raw_value, 1_000_000)
    return {"raw": str(raw_value), "decimal": f"{whole}.{fraction:06d}"}


def ingest_dataset_catalog(
    rpc: PolygonRpc,
    challenges: range,
    destination: Path,
    *,
    block_number: int | None = None,
) -> dict[str, Any]:
    observed_block = rpc.block_number() if block_number is None else block_number
    block = hex(observed_block)
    rows = []
    for challenge in challenges:
        digests = {
            name: read_bytes32(
                rpc,
                address,
                "getDatasetHash(uint32)",
                challenge,
                block=block,
            )
            for name, address in CONTRACTS.items()
        }
        if len(set(digests.values())) != 1:
            raise ValueError(f"competition dataset digests differ for challenge {challenge}")
        rows.append(
            {
                "challenge": challenge,
                "dataset": content_reference(next(iter(digests.values()))),
                "contract_digests": digests,
            }
        )
    catalog = {
        "schema_version": 1,
        "chain_id": CHAIN_ID,
        "observed_block": observed_block,
        "datasets": rows,
    }
    write_canonical_json(destination, catalog)
    return catalog


def ingest_challenge(
    rpc: PolygonRpc,
    challenge: int,
    destination: Path,
    *,
    block_number: int | None = None,
) -> dict[str, Any]:
    observed_block = rpc.block_number() if block_number is None else block_number
    block = hex(observed_block)
    competitions = {
        name: _ingest_competition(rpc, address, challenge, block)
        for name, address in CONTRACTS.items()
    }
    dataset_digests = {
        item["content"]["dataset"]["digest"] for item in competitions.values()
    }
    if len(dataset_digests) != 1:
        raise ValueError(f"competition dataset digests differ for challenge {challenge}")
    manifest = {
        "schema_version": 1,
        "chain_id": CHAIN_ID,
        "challenge": challenge,
        "observed_block": observed_block,
        "competitions": competitions,
    }
    write_canonical_json(destination, manifest)
    return manifest


def ingest_challenges(
    rpc: PolygonRpc,
    challenges: range,
    destination: Path,
) -> list[dict[str, Any]]:
    chain_id = rpc.chain_id()
    if chain_id != CHAIN_ID:
        raise ValueError(f"expected Polygon chain {CHAIN_ID}, got {chain_id}")
    observed_block = rpc.block_number()
    return [
        ingest_challenge(
            rpc,
            challenge,
            destination / f"challenge-{challenge:03d}.json",
            block_number=observed_block,
        )
        for challenge in challenges
    ]


def _ingest_competition(
    rpc: PolygonRpc,
    contract: str,
    challenge: int,
    block: str,
) -> dict[str, Any]:
    content = {
        field: content_reference(
            read_bytes32(rpc, contract, signature, challenge, block=block)
        )
        for field, signature in _CONTENT_FIELDS.items()
    }
    submitters = set(
        read_addresses(
            rpc, contract, "getAllSubmitters(uint32)", challenge, block=block
        )
    )
    historical_stakers = set(
        read_addresses(
            rpc, contract, "getHistoricalStakers(uint32)", challenge, block=block
        )
    )
    addresses = sorted(submitters | historical_stakers)

    calls = []
    call_fields: list[tuple[str, str]] = []
    for address in addresses:
        calls.append(
            participant_call(
                contract, "getSubmission(uint32,address)", challenge, address
            )
        )
        call_fields.append((address, "submission"))
        for field, signature in _PARTICIPANT_FIELDS.items():
            calls.append(participant_call(contract, signature, challenge, address))
            call_fields.append((address, field))

    records = {
        address: {
            "address": address,
            "is_submitter": address in submitters,
            "is_historical_staker": address in historical_stakers,
        }
        for address in addresses
    }
    for (address, field), result in zip(
        call_fields,
        rpc.multicall(calls, REGISTRY_ADDRESS, block=block),
        strict=True,
    ):
        if field == "submission":
            digest = decode_bytes32(result)
            records[address][field] = (
                None if digest == ZERO_BYTES32 else content_reference(digest)
            )
        else:
            records[address][field] = token_amount(decode_uint(result))

    return {
        "contract": contract,
        "content": content,
        "phase": read_uint(
            rpc, contract, "getPhase(uint32)", challenge, block=block
        ),
        "challenge_opened_block": read_uint(
            rpc,
            contract,
            "challengeOpenedBlockNumbers(uint32)",
            challenge,
            block=block,
        ),
        "submission_closed_block": read_uint(
            rpc,
            contract,
            "submissionClosedBlockNumbers(uint32)",
            challenge,
            block=block,
        ),
        "submitter_count": len(submitters),
        "historical_staker_count": len(historical_stakers),
        "participants": list(records.values()),
    }
