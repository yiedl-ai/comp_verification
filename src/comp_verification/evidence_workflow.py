"""Range-aware collection of immutable competition evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .chain_evidence import (
    ingest_event_provenance,
    verify_tracked_events,
    verify_tracked_snapshots,
)
from .config import VerifierConfig
from .datasets import (
    extract_latest_targets,
    verify_target_fixture,
    write_target_fixture,
)
from .encoding import digest_to_cid_v0, file_cid_v0
from .ingestion import ingest_challenges, ingest_dataset_catalog
from .ipfs import DownloadedArtifact, IpfsGateway, ProgressCallback
from .rpc import PolygonRpc


@dataclass(frozen=True)
class EvidenceWorkflow:
    """Collect evidence within the inclusive bounds configured in ``[scope]``."""

    root: Path
    config: VerifierConfig

    @classmethod
    def from_config(
        cls, root: Path, config_path: Path | None = None
    ) -> "EvidenceWorkflow":
        path = root / "config.toml" if config_path is None else config_path
        return cls(root=root, config=VerifierConfig.load(path))

    @property
    def rpc(self) -> PolygonRpc:
        settings = self.config.rpc
        return PolygonRpc(
            settings.url,
            timeout=settings.timeout_seconds,
            attempts=settings.attempts,
            retry_base_delay=settings.retry_base_delay_seconds,
            json_batch_size=settings.json_batch_size,
            json_batch_interval=settings.json_batch_interval_seconds,
            multicall_batch_size=settings.multicall_batch_size,
            log_block_span=settings.log_block_span,
        )

    @property
    def ipfs(self) -> IpfsGateway:
        settings = self.config.ipfs
        return IpfsGateway(
            settings.gateway_url,
            self.root / ".cache" / "ipfs",
            user_agent=settings.user_agent,
            timeout=settings.timeout_seconds,
            attempts=settings.attempts,
            retry_base_delay=settings.retry_base_delay_seconds,
            chunk_size=settings.chunk_size_bytes,
            max_concurrent_downloads=settings.max_concurrent_downloads,
        )

    def ingest_chain(
        self,
        *,
        challenges: Iterable[int] | None = None,
        dataset_challenges: Iterable[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Pin one block and collect snapshots plus the dataset catalog there."""

        rpc = self.rpc
        observed_block = rpc.block_number()
        manifests = self.ingest_chain_snapshots(
            challenges=challenges,
            observed_block=observed_block,
            rpc=rpc,
        )
        self.ingest_dataset_catalog(
            challenges=dataset_challenges,
            observed_block=observed_block,
            rpc=rpc,
        )
        return manifests

    def ingest_chain_snapshots(
        self,
        *,
        challenges: Iterable[int] | None = None,
        observed_block: int | None = None,
        rpc: PolygonRpc | None = None,
    ) -> list[dict[str, Any]]:
        """Collect a bounded challenge batch; useful for resumable ingestion."""

        selected = self._select_challenges(
            challenges, self.config.scope.chain_challenges, "challenge"
        )
        client = self.rpc if rpc is None else rpc
        return ingest_challenges(
            client,
            selected,
            self.root / "manifests" / "chain",
            block_number=observed_block,
        )

    def ingest_dataset_catalog(
        self,
        *,
        challenges: Iterable[int] | None = None,
        observed_block: int | None = None,
        rpc: PolygonRpc | None = None,
    ) -> dict[str, Any]:
        """Collect the configured dataset range using contract-level multicall."""

        selected = self._select_challenges(
            challenges, self.config.scope.dataset_challenges, "dataset challenge"
        )
        client = self.rpc if rpc is None else rpc
        return ingest_dataset_catalog(
            client,
            selected,
            self.root / "manifests" / "datasets.json",
            block_number=observed_block,
        )

    def verify_chain(self) -> dict[str, Any]:
        """Re-query every tracked snapshot and catalog entry at its pinned block."""

        return verify_tracked_snapshots(
            self.rpc,
            self.root / "manifests" / "chain",
            self.root / "manifests" / "datasets.json",
            self.root / ".cache" / "chain-verification",
            self.root / "reports" / "chain" / "snapshot-verification.json",
        )

    def ingest_chain_events(
        self, *, challenges: Iterable[int] | None = None
    ) -> list[dict[str, Any]]:
        """Capture lifecycle logs for an explicit, configured challenge set."""

        rpc = self.rpc
        reports = []
        for manifest in self._chain_manifests(challenges):
            challenge = manifest["challenge"]
            reports.append(
                ingest_event_provenance(
                    rpc,
                    manifest,
                    self.root
                    / "manifests"
                    / "chain-events"
                    / f"challenge-{challenge:03d}.json",
                )
            )
        return reports

    def verify_chain_events(self) -> dict[str, Any]:
        """Re-query and exactly compare all currently tracked lifecycle logs."""

        return verify_tracked_events(
            self.rpc,
            self.root / "manifests" / "chain",
            self.root / "manifests" / "chain-events",
            self.root / ".cache" / "chain-event-verification",
            self.root / "reports" / "chain" / "event-verification.json",
        )

    def download_datasets(
        self,
        *,
        challenges: Iterable[int] | None = None,
        progress: ProgressCallback | None = None,
    ) -> list[DownloadedArtifact]:
        """Download only selected catalog entries; no download occurs on construction."""

        selected = self._select_challenges(
            challenges, self.config.scope.dataset_challenges, "dataset challenge"
        )
        catalog = self._dataset_catalog_by_challenge()
        missing = [challenge for challenge in selected if challenge not in catalog]
        if missing:
            raise ValueError(f"dataset catalog is missing challenges: {missing}")
        cids = [catalog[challenge]["dataset"]["cid"] for challenge in selected]
        unavailable = [
            challenge for challenge, cid in zip(selected, cids, strict=True) if not cid
        ]
        if unavailable:
            raise ValueError(f"datasets have no published CID: {unavailable}")
        return self.ipfs.download_many(cids, progress=progress)

    def download_chain_evidence(
        self,
        *,
        challenges: Iterable[int] | None = None,
        progress: ProgressCallback | None = None,
    ) -> list[DownloadedArtifact]:
        """Download keys, results, and submissions referenced by selected snapshots."""

        cids: set[str] = set()
        for manifest in self._chain_manifests(challenges):
            for competition in manifest["competitions"].values():
                for name in ("private_key", "results"):
                    if cid := competition["content"][name]["cid"]:
                        cids.add(cid)
                for participant in competition["participants"]:
                    submission = participant["submission"]
                    if submission and submission["cid"]:
                        cids.add(submission["cid"])
        return self.ipfs.download_many(cids, progress=progress)

    def condense_score_ready_datasets(
        self,
        *,
        scoring_challenges: Iterable[int] | None = None,
        progress: ProgressCallback | None = None,
        prune_raw: bool = False,
    ) -> list[dict[str, Any]]:
        """Sequentially verify, condense, re-verify, and optionally prune datasets."""

        selected = self._select_challenges(
            scoring_challenges,
            self.config.scope.score_ready_challenges,
            "score-ready challenge",
        )
        catalog = self._dataset_catalog_by_challenge()
        gateway = self.ipfs
        completed = []
        for scoring_challenge in selected:
            source_challenge = scoring_challenge + 1
            if source_challenge not in catalog:
                raise ValueError(
                    f"dataset catalog is missing challenge {source_challenge}"
                )
            reference = catalog[source_challenge]["dataset"]
            source_cid = reference["cid"]
            source_digest = reference["digest"]
            if not source_cid:
                raise ValueError(f"dataset {source_challenge} has no published CID")
            if digest_to_cid_v0(source_digest) != source_cid:
                raise ValueError(
                    f"dataset {source_challenge} CID differs from its on-chain digest"
                )

            # This is intentionally one-at-a-time so a large archive is pruned before
            # the next download begins, keeping peak cache growth bounded.
            artifact = gateway.download(source_cid, progress=progress)
            computed_cid = file_cid_v0(artifact.path)
            if computed_cid != source_cid:
                raise ValueError(
                    f"dataset {source_challenge} bytes differ from CID {source_cid}"
                )
            targets, member = extract_latest_targets(
                artifact.path,
                scoring_challenge=scoring_challenge,
                source_dataset_challenge=source_challenge,
                source_cid=source_cid,
                source_digest=source_digest,
            )
            destination = (
                self.root
                / "data"
                / "targets"
                / f"challenge-{scoring_challenge:03d}.csv"
            )
            write_target_fixture(
                targets,
                member,
                artifact.sha256,
                artifact.size,
                computed_cid,
                destination,
            )

            # Re-open and re-extract from raw bytes before they become eligible for
            # deletion; verification does not reuse the in-memory extraction.
            checked_targets, checked_member = extract_latest_targets(
                artifact.path,
                scoring_challenge=scoring_challenge,
                source_dataset_challenge=source_challenge,
                source_cid=source_cid,
                source_digest=source_digest,
            )
            verify_target_fixture(
                checked_targets,
                checked_member,
                artifact.sha256,
                artifact.size,
                computed_cid,
                destination,
            )
            if prune_raw:
                gateway.prune_verified_artifact(artifact)
            completed.append(
                {
                    "scoring_challenge": scoring_challenge,
                    "source_dataset_challenge": source_challenge,
                    "source_cid": source_cid,
                    "source_archive_sha256": artifact.sha256,
                    "target_date": checked_targets.date,
                    "target_columns": list(checked_targets.target_columns),
                    "symbol_count": len(checked_targets.rows),
                    "fixture": str(destination.relative_to(self.root)),
                    "raw_pruned": prune_raw,
                }
            )
        return completed

    def _chain_manifests(
        self, challenges: Iterable[int] | None = None
    ) -> list[dict[str, Any]]:
        selected = self._select_challenges(
            challenges, self.config.scope.chain_challenges, "challenge"
        )
        manifests = []
        missing = []
        for challenge in selected:
            path = self.root / "manifests" / "chain" / f"challenge-{challenge:03d}.json"
            if not path.exists():
                missing.append(challenge)
                continue
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        if missing:
            raise ValueError(f"chain manifests are missing challenges: {missing}")
        return manifests

    def _dataset_catalog_by_challenge(self) -> dict[int, dict[str, Any]]:
        path = self.root / "manifests" / "datasets.json"
        catalog = json.loads(path.read_text(encoding="utf-8"))
        return {row["challenge"]: row for row in catalog["datasets"]}

    @staticmethod
    def _select_challenges(
        requested: Iterable[int] | None,
        configured: range,
        label: str,
    ) -> list[int]:
        selected = list(configured if requested is None else requested)
        if not selected:
            raise ValueError(f"{label} selection must not be empty")
        if len(selected) != len(set(selected)):
            raise ValueError(f"{label} selection contains duplicates")
        outside = [challenge for challenge in selected if challenge not in configured]
        if outside:
            raise ValueError(
                f"{label} selection exceeds configured scope: {outside}"
            )
        return selected
