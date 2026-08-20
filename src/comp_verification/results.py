"""Parse published result CSVs and reconcile them with contract observations."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PublishedResult:
    address: str
    competition: str
    challenge: int
    relative_gain: Decimal
    wallet_reward: Decimal
    stake: Decimal


def read_published_results(
    path: Path, *, competition: str, challenge: int
) -> dict[str, PublishedResult]:
    rows: dict[str, PublishedResult] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "address",
            "competition",
            "challenge",
            "relative_gain",
            "wallet_reward",
            "stake",
        }
        fields = set(reader.fieldnames or ())
        if not required <= fields:
            raise ValueError(f"results file lacks columns {sorted(required - fields)}")
        for source in reader:
            row = _parse_row(source)
            if row.competition != competition:
                raise ValueError(
                    f"expected competition {competition}, found {row.competition}"
                )
            if row.challenge != challenge:
                raise ValueError(f"expected challenge {challenge}, found {row.challenge}")
            if row.address in rows:
                raise ValueError(f"duplicate result address {row.address}")
            rows[row.address] = row
    return rows


def compare_results_to_chain(
    manifest: dict[str, Any],
    competition: str,
    results: dict[str, PublishedResult],
) -> dict[str, Any]:
    observed = manifest["competitions"][competition]
    participants = {row["address"]: row for row in observed["participants"]}
    mismatches: list[dict[str, str]] = []

    for address in sorted(participants.keys() | results.keys()):
        chain = participants.get(address)
        published = results.get(address)
        if chain is None:
            mismatches.append(
                {"address": address, "field": "participant", "detail": "missing on chain"}
            )
            continue
        if published is None:
            mismatches.append(
                {"address": address, "field": "participant", "detail": "missing in results"}
            )
            continue
        _compare_decimal(
            mismatches,
            address,
            "stake",
            Decimal(chain["historical_stake"]["decimal"]),
            published.stake,
        )
        expected_reward = max(published.wallet_reward, Decimal(0))
        expected_burn = max(-published.wallet_reward, Decimal(0))
        _compare_decimal(
            mismatches,
            address,
            "challenge_reward",
            Decimal(chain["challenge_reward"]["decimal"]),
            expected_reward,
        )
        _compare_decimal(
            mismatches,
            address,
            "burned",
            Decimal(chain["burned"]["decimal"]),
            expected_burn,
        )

    return {
        "schema_version": 1,
        "challenge": manifest["challenge"],
        "competition": competition,
        "contract": observed["contract"],
        "observed_block": manifest["observed_block"],
        "result_cid": observed["content"]["results"]["cid"],
        "chain_participant_count": len(participants),
        "published_row_count": len(results),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "passed": not mismatches,
    }


def _parse_row(source: dict[str, str]) -> PublishedResult:
    address = (source.get("address") or "").strip().lower()
    if not address.startswith("0x") or len(address) != 42:
        raise ValueError(f"invalid result address {address!r}")
    try:
        return PublishedResult(
            address=address,
            competition=(source.get("competition") or "").strip(),
            challenge=int(source.get("challenge") or ""),
            relative_gain=Decimal(source.get("relative_gain") or ""),
            wallet_reward=Decimal(source.get("wallet_reward") or ""),
            stake=Decimal(source.get("stake") or ""),
        )
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"invalid result row for {address}") from error


def _compare_decimal(
    mismatches: list[dict[str, str]],
    address: str,
    field: str,
    chain: Decimal,
    published: Decimal,
) -> None:
    if chain != published:
        mismatches.append(
            {
                "address": address,
                "field": field,
                "chain": str(chain),
                "published": str(published),
            }
        )
