"""Verify tracked chain snapshots and preserve their event provenance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import CHAIN_ID
from .encoding import event_topic
from .ingestion import ingest_challenge, ingest_dataset_catalog
from .jsonio import canonical_json_bytes, write_canonical_json
from .rpc import PolygonRpc, read_uint


@dataclass(frozen=True)
class EventDefinition:
    name: str
    signature: str
    challenge_location: str | None

    @property
    def topic(self) -> str:
        return event_topic(self.signature)


_EVENTS = (
    EventDefinition("SubmissionUpdated", "SubmissionUpdated(uint32,address,bytes32)", "topic"),
    EventDefinition("PrivateKeyUpdated", "PrivateKeyUpdated(bytes32)", None),
    EventDefinition("ChallengeOpened", "ChallengeOpened(uint32)", "topic"),
    EventDefinition("DatasetUpdated", "DatasetUpdated(uint32,bytes32,bytes32)", "topic"),
    EventDefinition("KeyUpdated", "KeyUpdated(uint32,bytes32,bytes32)", "topic"),
    EventDefinition("SubmissionClosed", "SubmissionClosed(uint32)", "topic"),
    EventDefinition("ResultsUpdated", "ResultsUpdated(uint32,bytes32,bytes32)", "topic"),
    EventDefinition("RewardsPayment", "RewardsPayment(uint32,address,uint256,uint256,uint256)", "data"),
    EventDefinition("TotalRewardsPaid", "TotalRewardsPaid(uint32,uint256,uint256,uint256)", "data"),
    EventDefinition(
        "ChallengeAndTournamentScoresUpdated",
        "ChallengeAndTournamentScoresUpdated(uint32)",
        "topic",
    ),
    EventDefinition("BatchInformationUpdated", "BatchInformationUpdated(uint32,uint256)", "topic"),
    EventDefinition("BackedParticipantUpdated", "BackedParticipantUpdated(uint32,address,address)", "topic"),
    EventDefinition("BurnMaxUpdated", "BurnMaxUpdated(uint32,uint256,uint256,uint256)", "topic"),
    EventDefinition("Burned", "Burned(uint32,address,uint256)", "topic"),
)
_EVENT_BY_TOPIC = {definition.topic: definition for definition in _EVENTS}


def verify_tracked_snapshots(
    rpc: PolygonRpc,
    chain_directory: Path,
    dataset_catalog_path: Path,
    scratch_directory: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Re-query every tracked value at its pinned block and compare exactly."""

    chain_id = rpc.chain_id()
    if chain_id != CHAIN_ID:
        raise ValueError(f"expected Polygon chain {CHAIN_ID}, got {chain_id}")
    scratch_directory.mkdir(parents=True, exist_ok=True)
    comparisons: list[dict[str, Any]] = []
    manifests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(chain_directory.glob("challenge-*.json"))
    ]
    for expected in manifests:
        challenge = expected["challenge"]
        destination = scratch_directory / f"challenge-{challenge:03d}.json"
        actual = ingest_challenge(
            rpc,
            challenge,
            destination,
            block_number=expected["observed_block"],
        )
        comparisons.append(
            _comparison(f"manifests/chain/challenge-{challenge:03d}.json", expected, actual)
        )

    expected_catalog = json.loads(dataset_catalog_path.read_text(encoding="utf-8"))
    dataset_challenges = [row["challenge"] for row in expected_catalog["datasets"]]
    actual_catalog = ingest_dataset_catalog(
        rpc,
        dataset_challenges,
        scratch_directory / "datasets.json",
        block_number=expected_catalog["observed_block"],
    )
    comparisons.append(
        _comparison("manifests/datasets.json", expected_catalog, actual_catalog)
    )
    report = {
        "schema_version": 1,
        "chain_id": CHAIN_ID,
        "comparison_count": len(comparisons),
        "mismatch_count": sum(not item["passed"] for item in comparisons),
        "passed": all(item["passed"] for item in comparisons),
        "comparisons": comparisons,
    }
    write_canonical_json(report_path, report)
    return report


def ingest_event_provenance(
    rpc: PolygonRpc,
    manifest: dict[str, Any],
    destination: Path,
) -> dict[str, Any]:
    """Capture challenge-scoped lifecycle logs with block and transaction hashes."""

    observed_block = manifest["observed_block"]
    challenge = manifest["challenge"]
    competitions: dict[str, Any] = {}
    for competition, snapshot in manifest["competitions"].items():
        contract = snapshot["contract"]
        start = snapshot["challenge_opened_block"]
        next_open = read_uint(
            rpc,
            contract,
            "challengeOpenedBlockNumbers(uint32)",
            challenge + 1,
            block=hex(observed_block),
        )
        end = observed_block if next_open == 0 else next_open - 1
        logs = rpc.get_logs(
            contract,
            start,
            end,
            topic0=list(_EVENT_BY_TOPIC),
        )
        events = []
        for log in logs:
            normalized = _normalize_event(log, challenge)
            if normalized is not None:
                events.append(normalized)
        events.sort(key=lambda item: (item["block_number"], item["transaction_index"], item["log_index"]))
        competitions[competition] = {
            "contract": contract,
            "from_block": start,
            "to_block": end,
            "event_count": len(events),
            "events": events,
        }
    evidence = {
        "schema_version": 1,
        "chain_id": CHAIN_ID,
        "challenge": challenge,
        "snapshot_block": observed_block,
        "competitions": competitions,
    }
    write_canonical_json(destination, evidence)
    return evidence


def verify_tracked_events(
    rpc: PolygonRpc,
    chain_directory: Path,
    event_directory: Path,
    scratch_directory: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Re-query tracked lifecycle events and compare their raw log evidence."""

    chain_id = rpc.chain_id()
    if chain_id != CHAIN_ID:
        raise ValueError(f"expected Polygon chain {CHAIN_ID}, got {chain_id}")
    scratch_directory.mkdir(parents=True, exist_ok=True)
    comparisons: list[dict[str, Any]] = []
    for manifest_path in sorted(chain_directory.glob("challenge-*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        challenge = manifest["challenge"]
        tracked_path = event_directory / f"challenge-{challenge:03d}.json"
        expected = json.loads(tracked_path.read_text(encoding="utf-8"))
        actual = ingest_event_provenance(
            rpc,
            manifest,
            scratch_directory / tracked_path.name,
        )
        comparisons.append(
            _comparison(
                f"manifests/chain-events/{tracked_path.name}",
                expected,
                actual,
                block_key="snapshot_block",
            )
        )
    report = {
        "schema_version": 1,
        "chain_id": CHAIN_ID,
        "comparison_count": len(comparisons),
        "mismatch_count": sum(not item["passed"] for item in comparisons),
        "passed": all(item["passed"] for item in comparisons),
        "comparisons": comparisons,
    }
    write_canonical_json(report_path, report)
    return report


def _normalize_event(log: dict[str, Any], challenge: int) -> dict[str, Any] | None:
    topics = log.get("topics")
    data = log.get("data")
    if not isinstance(topics, list) or not topics or not isinstance(data, str):
        return None
    definition = _EVENT_BY_TOPIC.get(str(topics[0]).lower())
    if definition is None:
        return None
    event_challenge: int | None = None
    if definition.challenge_location == "topic":
        if len(topics) < 2:
            return None
        event_challenge = int(topics[1], 16)
    elif definition.challenge_location == "data":
        raw = data.removeprefix("0x")
        if len(raw) < 64:
            return None
        event_challenge = int(raw[:64], 16)
    if event_challenge is not None and event_challenge != challenge:
        return None
    return {
        "event": definition.name,
        "block_number": int(log["blockNumber"], 16),
        "block_hash": log["blockHash"].lower(),
        "transaction_hash": log["transactionHash"].lower(),
        "transaction_index": int(log["transactionIndex"], 16),
        "log_index": int(log["logIndex"], 16),
        "topics": [str(topic).lower() for topic in topics],
        "data": data.lower(),
    }


def _comparison(
    name: str,
    expected: Any,
    actual: Any,
    *,
    block_key: str = "observed_block",
) -> dict[str, Any]:
    differences: list[dict[str, Any]] = []
    _diff(expected, actual, "$", differences)
    return {
        "artifact": name,
        "pinned_block": expected[block_key],
        "tracked_sha256": hashlib.sha256(canonical_json_bytes(expected)).hexdigest(),
        "queried_sha256": hashlib.sha256(canonical_json_bytes(actual)).hexdigest(),
        "difference_count": len(differences),
        "differences": differences,
        "passed": not differences,
    }


def _diff(expected: Any, actual: Any, path: str, output: list[dict[str, Any]]) -> None:
    if type(expected) is not type(actual):
        output.append({"path": path, "tracked": expected, "queried": actual})
    elif isinstance(expected, dict):
        for key in sorted(expected.keys() | actual.keys()):
            child = f"{path}.{key}"
            if key not in expected:
                output.append({"path": child, "tracked": "<missing>", "queried": actual[key]})
            elif key not in actual:
                output.append({"path": child, "tracked": expected[key], "queried": "<missing>"})
            else:
                _diff(expected[key], actual[key], child, output)
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            output.append({"path": f"{path}.length", "tracked": len(expected), "queried": len(actual)})
        for index, (left, right) in enumerate(zip(expected, actual)):
            _diff(left, right, f"{path}[{index}]", output)
    elif expected != actual:
        output.append({"path": path, "tracked": expected, "queried": actual})
