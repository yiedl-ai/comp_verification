"""Deterministic normalized submission fixtures retained after IPFS pruning."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from .jsonio import canonical_json_bytes
from .policies import ScoringPolicy


NormalizedSubmissions = dict[str, dict[str, Decimal]]


def write_submission_fixture(
    destination: Path,
    *,
    challenge: int,
    competition: str,
    policy: ScoringPolicy,
    predictions: Mapping[str, Mapping[str, Decimal]],
    participant_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write scorer-ready predictions plus provenance for every valid address."""

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("address", "symbol", "prediction"))
    row_count = 0
    for address in sorted(predictions):
        values = predictions[address]
        for symbol in policy.symbols:
            if symbol not in values:
                raise ValueError(f"{address} is missing normalized symbol {symbol}")
            writer.writerow((address, symbol, str(values[symbol])))
            row_count += 1
    rendered = output.getvalue().encode("utf-8")
    evidence_by_address = {
        row["address"]: row for row in participant_evidence if row["status"] == "valid"
    }
    if set(evidence_by_address) != set(predictions):
        raise ValueError("valid participant evidence differs from normalized addresses")
    provenance = {
        "schema_version": 1,
        "challenge": challenge,
        "competition": competition,
        "policy_id": policy.policy_id,
        "policy_source_git_commit": policy.source_git_commit,
        "address_count": len(predictions),
        "row_count": row_count,
        "fixture_sha256": hashlib.sha256(rendered).hexdigest(),
        "submissions": [
            {
                key: evidence_by_address[address][key]
                for key in (
                    "address",
                    "submission_cid",
                    "archive_sha256",
                    "predictions_sha256",
                    "prediction_count",
                )
            }
            for address in sorted(predictions)
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(rendered)
    destination.with_suffix(".json").write_bytes(canonical_json_bytes(provenance))
    return provenance


def read_submission_fixture(
    source: Path, *, policy: ScoringPolicy
) -> NormalizedSubmissions:
    """Read and validate a committed normalized fixture before scoring."""

    rendered = source.read_bytes()
    provenance = json.loads(source.with_suffix(".json").read_text(encoding="utf-8"))
    if hashlib.sha256(rendered).hexdigest() != provenance.get("fixture_sha256"):
        raise ValueError(f"submission fixture hash differs from provenance: {source}")
    if provenance.get("policy_id") != policy.policy_id:
        raise ValueError(f"submission fixture policy differs from scorer: {source}")
    reader = csv.DictReader(io.StringIO(rendered.decode("utf-8-sig")))
    if reader.fieldnames != ["address", "symbol", "prediction"]:
        raise ValueError(f"unexpected submission fixture columns: {source}")
    output: NormalizedSubmissions = {}
    allowed = set(policy.symbols)
    row_count = 0
    for row in reader:
        address = (row.get("address") or "").lower()
        symbol = (row.get("symbol") or "").strip()
        if not address or symbol not in allowed:
            raise ValueError(f"invalid normalized submission row: {source}")
        values = output.setdefault(address, {})
        if symbol in values:
            raise ValueError(f"duplicate normalized symbol {address} {symbol}")
        try:
            value = Decimal((row.get("prediction") or "").strip())
        except InvalidOperation as error:
            raise ValueError(f"invalid normalized prediction {address} {symbol}") from error
        if not value.is_finite():
            raise ValueError(f"non-finite normalized prediction {address} {symbol}")
        values[symbol] = value
        row_count += 1
    for address, values in output.items():
        if set(values) != allowed:
            raise ValueError(f"normalized submission symbols differ for {address}")
        output[address] = {symbol: values[symbol] for symbol in policy.symbols}
    if row_count != provenance.get("row_count") or len(output) != provenance.get(
        "address_count"
    ):
        raise ValueError(f"submission fixture counts differ from provenance: {source}")
    return output
