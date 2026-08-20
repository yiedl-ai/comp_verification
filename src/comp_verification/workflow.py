"""Fixed, importable workflow for the first ten historical challenges."""

from __future__ import annotations

import hashlib
import json
import platform
import zipfile
from decimal import Decimal
from dataclasses import dataclass, replace
from importlib.metadata import version
from pathlib import Path
from typing import Any

from .caveats import caveats_for_context
from .constants import (
    FIRST_CHALLENGE,
    IPFS_GATEWAY,
    LAST_CHALLENGE,
    LAST_DATASET_CHALLENGE,
)
from .config import VerifierConfig
from .corrections import load_verified_result_correction
from .correction_40_42 import audit_correction_sequence
from .datasets import (
    derive_price_fixture_from_targets,
    extract_latest_realized_returns,
    verify_price_fixture,
    write_price_fixture,
)
from .ingestion import ingest_challenges, ingest_dataset_catalog
from .ipfs import DownloadedArtifact, IpfsGateway, ProgressCallback
from .rpc import PolygonRpc
from .results import compare_results_to_chain, read_published_results
from .jsonio import write_canonical_json
from .policies import (
    DYNAMIC_SYMBOL_ALIASES,
    LEGACY_30_CANDIDATE,
    ScoringPolicy,
    policy_for_challenge,
)
from .submissions import (
    InvalidSubmission,
    decrypt_submission_archive,
    parse_dynamic_predictions,
    parse_predictions,
)
from .submission_fixtures import read_submission_fixture, write_submission_fixture
from .ipfs import IpfsDownloadError
from .scoring import read_realized_returns, score_prediction
from .chain_evidence import (
    ingest_event_provenance,
    verify_tracked_events,
    verify_tracked_snapshots,
)
from .summary import build_audit_status, build_first_ten_summary


@dataclass(frozen=True)
class FirstTenWorkflow:
    root: Path
    config: VerifierConfig

    @classmethod
    def from_config(
        cls, root: Path, config_path: Path | None = None
    ) -> "FirstTenWorkflow":
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
            gateway_token=settings.gateway_token,
            timeout=settings.timeout_seconds,
            attempts=settings.attempts,
            retry_base_delay=settings.retry_base_delay_seconds,
            chunk_size=settings.chunk_size_bytes,
            max_concurrent_downloads=settings.max_concurrent_downloads,
        )

    def ingest_chain(self) -> list[dict[str, Any]]:
        rpc = self.rpc
        manifests = ingest_challenges(
            rpc,
            range(FIRST_CHALLENGE, LAST_CHALLENGE + 1),
            self.root / "manifests" / "chain",
        )
        ingest_dataset_catalog(
            rpc,
            range(FIRST_CHALLENGE, LAST_DATASET_CHALLENGE + 1),
            self.root / "manifests" / "datasets.json",
            block_number=manifests[0]["observed_block"],
        )
        return manifests

    def verify_chain(self) -> dict[str, Any]:
        """Re-query the tracked snapshots at their pinned historical block."""

        return verify_tracked_snapshots(
            self.rpc,
            self.root / "manifests" / "chain",
            self.root / "manifests" / "datasets.json",
            self.root / ".cache" / "chain-verification",
            self.root / "reports" / "chain" / "snapshot-verification.json",
        )

    def ingest_chain_events(self) -> list[dict[str, Any]]:
        """Capture deterministic lifecycle logs for all first-ten challenges."""

        rpc = self.rpc
        reports = []
        for manifest in self._chain_manifests():
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
        """Re-query and exactly compare all tracked lifecycle logs."""

        return verify_tracked_events(
            self.rpc,
            self.root / "manifests" / "chain",
            self.root / "manifests" / "chain-events",
            self.root / ".cache" / "chain-event-verification",
            self.root / "reports" / "chain" / "event-verification.json",
        )

    def download_datasets(
        self, *, progress: ProgressCallback | None = None
    ) -> list[DownloadedArtifact]:
        catalog = self._dataset_catalog()
        return self.ipfs.download_many(
            [row["dataset"]["cid"] for row in catalog["datasets"]],
            progress=progress,
        )

    def download_chain_evidence(
        self, *, progress: ProgressCallback | None = None
    ) -> list[DownloadedArtifact]:
        cids: set[str] = set()
        for manifest_path in sorted((self.root / "manifests" / "chain").glob("*.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for competition in manifest["competitions"].values():
                for name in ("private_key", "results"):
                    cid = competition["content"][name]["cid"]
                    if cid:
                        cids.add(cid)
                for participant in competition["participants"]:
                    submission = participant["submission"]
                    if submission and submission["cid"]:
                        cids.add(submission["cid"])
        return self.ipfs.download_many(cids, progress=progress)

    def download_results(
        self, *, progress: ProgressCallback | None = None
    ) -> list[DownloadedArtifact]:
        return self.ipfs.download_many(self._content_cids("results"), progress=progress)

    def download_private_keys(
        self,
        *,
        progress: ProgressCallback | None = None,
        challenges: range | None = None,
    ) -> list[DownloadedArtifact]:
        return self.ipfs.download_many(
            self._content_cids("private_key", challenges), progress=progress
        )

    def download_submissions(
        self, *, progress: ProgressCallback | None = None
    ) -> list[DownloadedArtifact]:
        cids: set[str] = set()
        for manifest in self._chain_manifests():
            for competition in manifest["competitions"].values():
                for participant in competition["participants"]:
                    submission = participant["submission"]
                    if submission and submission["cid"]:
                        cids.add(submission["cid"])
        return self.ipfs.download_many(cids, progress=progress)

    def prune_condensed_chain_evidence(
        self, *, challenges: range
    ) -> list[dict[str, Any]]:
        """Prune cached chain-linked IPFS bytes after committed evidence exists."""

        dataset_cids = {
            row["dataset"]["cid"] for row in self._dataset_catalog()["datasets"]
        }
        candidates: set[str] = set()
        for manifest in self._chain_manifests(challenges):
            challenge = manifest["challenge"]
            for competition, observed in manifest["competitions"].items():
                publication_path = (
                    self.root
                    / "reports"
                    / "publication"
                    / f"challenge-{challenge:03d}-{competition.lower()}.json"
                )
                submission_path = (
                    self.root
                    / "reports"
                    / "submissions"
                    / f"challenge-{challenge:03d}-{competition.lower()}.json"
                )
                fixture_path = self._submission_fixture_path(challenge, competition)
                required = (
                    publication_path,
                    submission_path,
                    fixture_path,
                    fixture_path.with_suffix(".json"),
                )
                missing = [str(path) for path in required if not path.is_file()]
                if missing:
                    raise FileNotFoundError(
                        f"refusing to prune challenge {challenge}: missing {missing}"
                    )
                publication = json.loads(publication_path.read_text(encoding="utf-8"))
                candidates.add(
                    publication.get("resolved_result_cid")
                    or observed["content"]["results"]["cid"]
                )
                candidates.add(observed["content"]["private_key"]["cid"])
                candidates.update(
                    participant["submission"]["cid"]
                    for participant in observed["participants"]
                    if participant["submission"]
                )
        gateway = self.ipfs
        pruned = []
        for cid in sorted(candidates - dataset_cids - {""}):
            path = gateway.cache / cid
            marker = gateway.cache / f"{cid}.complete"
            if not path.is_file() or not marker.is_file():
                continue
            artifact = gateway.download(cid)
            gateway.prune_verified_artifact(artifact)
            pruned.append(
                {"cid": cid, "size": artifact.size, "sha256": artifact.sha256}
            )
        return pruned

    def verify_publication(
        self,
        *,
        progress: ProgressCallback | None = None,
        challenges: range | None = None,
    ) -> list[dict[str, Any]]:
        reports = []
        for manifest in self._chain_manifests(challenges):
            for competition, observed in manifest["competitions"].items():
                special = self._correction_sequence_report(
                    manifest["challenge"], competition
                )
                if special is not None:
                    report = self._correction_publication_report(
                        manifest, competition, observed, special
                    )
                    destination = (
                        self.root
                        / "reports"
                        / "publication"
                        / f"challenge-{manifest['challenge']:03d}-{competition.lower()}.json"
                    )
                    write_canonical_json(destination, report)
                    reports.append(report)
                    continue
                cid = observed["content"]["results"]["cid"]
                correction = load_verified_result_correction(
                    self.root,
                    self.rpc,
                    challenge=manifest["challenge"],
                    competition=competition,
                    contract=observed["contract"],
                )
                resolved_cid = (
                    correction["corrected_content"]["cid"]
                    if correction is not None
                    else cid
                )
                destination = (
                    self.root
                    / "reports"
                    / "publication"
                    / f"challenge-{manifest['challenge']:03d}-{competition.lower()}.json"
                )
                artifact = None
                try:
                    if not resolved_cid:
                        raise ValueError("missing result CID")
                    artifact = self.ipfs.download(
                        resolved_cid,
                        expected_sha256=(
                            correction["corrected_content"]["bytes_sha256"]
                            if correction is not None
                            else None
                        ),
                        progress=progress,
                    )
                    published = read_published_results(
                        artifact.path,
                        competition=competition,
                        challenge=manifest["challenge"],
                    )
                    report = compare_results_to_chain(manifest, competition, published)
                    report["result_bytes_sha256"] = artifact.sha256
                    if correction is not None:
                        report.update(
                            {
                                "primary_result_cid": cid,
                                "resolved_result_cid": resolved_cid,
                                "resolution": "on-chain-information-correction",
                                "raw_primary_reference_passed": False,
                                "passed_with_caveat": report["passed"],
                                "correction_evidence": correction,
                                "caveats": caveats_for_context(
                                    challenge=manifest["challenge"],
                                    competition=competition,
                                    audit_kind="publication",
                                ),
                            }
                        )
                except (IpfsDownloadError, OSError, ValueError) as error:
                    caveats = caveats_for_context(
                        challenge=manifest["challenge"],
                        competition=competition,
                        audit_kind="publication",
                    )
                    report = {
                        "schema_version": 1,
                        "challenge": manifest["challenge"],
                        "competition": competition,
                        "contract": observed["contract"],
                        "observed_block": manifest["observed_block"],
                        "result_cid": cid,
                        "resolved_result_cid": resolved_cid,
                        "result_bytes_sha256": (
                            artifact.sha256 if artifact is not None else None
                        ),
                        "mismatch_count": 1,
                        "passed": False,
                        "problem": f"{type(error).__name__}: {error}",
                        "caveats": caveats,
                    }
                write_canonical_json(destination, report)
                reports.append(report)
        return reports

    def ingest_submissions(
        self,
        *,
        progress: ProgressCallback | None = None,
        challenges: range | None = None,
    ) -> list[dict[str, Any]]:
        self.download_private_keys(progress=progress, challenges=challenges)
        self._download_submission_scope(challenges, progress)
        reports = []
        for manifest in self._chain_manifests(challenges):
            policy = self._effective_policy(manifest["challenge"])
            for competition, observed in manifest["competitions"].items():
                private_key_cid = observed["content"]["private_key"]["cid"]
                if not private_key_cid:
                    raise ValueError(
                        f"missing private key for challenge {manifest['challenge']}"
                    )
                private_key = self.ipfs.download(private_key_cid).path
                participants = []
                for participant in observed["participants"]:
                    submission = participant["submission"]
                    if not submission:
                        participants.append(
                            {
                                "address": participant["address"],
                                "status": "no-submission",
                                "submission_cid": None,
                            }
                        )
                        continue
                    participants.append(
                        self._decrypt_one_submission(
                            manifest["challenge"],
                            competition,
                            participant["address"],
                            submission["cid"],
                            private_key,
                        )
                    )
                fixture_provenance = self._write_submission_fixture(
                    manifest["challenge"], competition, policy, participants
                )
                report = {
                    "schema_version": 1,
                    "challenge": manifest["challenge"],
                    "competition": competition,
                    "policy_id": policy.policy_id,
                    "policy_status": policy.status,
                    "private_key_cid": private_key_cid,
                    "participant_count": len(participants),
                    "valid_submission_count": sum(
                        item["status"] == "valid" for item in participants
                    ),
                    "normalized_fixture": fixture_provenance,
                    "participants": participants,
                }
                destination = (
                    self.root
                    / "reports"
                    / "submissions"
                    / f"challenge-{manifest['challenge']:03d}-{competition.lower()}.json"
                )
                write_canonical_json(destination, report)
                reports.append(report)
        return reports

    def audit_scoring(
        self,
        *,
        challenges: range | None = None,
        gain_tolerance: Decimal = Decimal(0),
    ) -> list[dict[str, Any]]:
        reports = []
        for manifest in self._chain_manifests(challenges):
            challenge = manifest["challenge"]
            policy = self._effective_policy(challenge)
            for competition, observed in manifest["competitions"].items():
                special = self._correction_sequence_report(challenge, competition)
                if special is not None:
                    report = self._correction_scoring_report(
                        manifest, competition, observed, special
                    )
                    destination = (
                        self.root
                        / "reports"
                        / "scoring"
                        / f"challenge-{challenge:03d}-{competition.lower()}.json"
                    )
                    write_canonical_json(destination, report)
                    reports.append(report)
                    continue
                returns = read_realized_returns(
                    self._price_fixture_path(challenge, competition),
                    binary_float=policy.answer_binary_float,
                    decimal_from_float_string=self._is_dynamic_policy(policy),
                )
                fixture_path = self._submission_fixture_path(challenge, competition)
                normalized_submissions = (
                    read_submission_fixture(
                        fixture_path,
                        policy=policy,
                        require_all_symbols=not self._is_dynamic_policy(policy),
                    )
                    if fixture_path.exists()
                    else None
                )
                submission_report_path = (
                    self.root
                    / "reports"
                    / "submissions"
                    / f"challenge-{challenge:03d}-{competition.lower()}.json"
                )
                submission_statuses = (
                    {
                        row["address"]: row["status"]
                        for row in json.loads(
                            submission_report_path.read_text(encoding="utf-8")
                        )["participants"]
                    }
                    if submission_report_path.exists()
                    else {}
                )
                result_cid = observed["content"]["results"]["cid"]
                publication_report = json.loads(
                    (
                        self.root
                        / "reports"
                        / "publication"
                        / f"challenge-{challenge:03d}-{competition.lower()}.json"
                    ).read_text(encoding="utf-8")
                )
                if not publication_report["passed"]:
                    report = {
                        "schema_version": 1,
                        "challenge": challenge,
                        "competition": competition,
                        "policy_id": policy.policy_id,
                        "policy_source_git_commit": policy.source_git_commit,
                        "policy_source_files_sha256": dict(
                            policy.source_files_sha256
                        ),
                        "policy_status": policy.status,
                        "result_cid": result_cid,
                        "result_bytes_sha256": publication_report.get(
                            "result_bytes_sha256"
                        ),
                        "participant_count": len(observed["participants"]),
                        "comparison_count": 0,
                        "mismatch_count": 0,
                        "audit_status": "blocked-by-publication-failure",
                        "raw_passed": False,
                        "passed": False,
                        "problem": publication_report.get("problem"),
                        "caveats": caveats_for_context(
                            challenge=challenge,
                            competition=competition,
                            audit_kind="scoring",
                        ),
                        "participants": [],
                    }
                    destination = (
                        self.root
                        / "reports"
                        / "scoring"
                        / f"challenge-{challenge:03d}-{competition.lower()}.json"
                    )
                    write_canonical_json(destination, report)
                    reports.append(report)
                    continue
                resolved_result_cid = publication_report.get(
                    "resolved_result_cid", result_cid
                )
                result_artifact = self.ipfs.download(
                    resolved_result_cid,
                    expected_sha256=publication_report["result_bytes_sha256"],
                )
                published = read_published_results(
                    result_artifact.path,
                    competition=competition,
                    challenge=challenge,
                )
                comparisons = []
                for participant in observed["participants"]:
                    address = participant["address"]
                    stake = Decimal(participant["historical_stake"]["decimal"])
                    computed_gain, computed_reward, status = self._score_participant(
                        challenge,
                        competition,
                        address,
                        participant["submission"],
                        stake,
                        returns,
                        policy,
                        normalized_prediction=(
                            normalized_submissions.get(address)
                            if normalized_submissions is not None
                            else None
                        ),
                        ingestion_status=submission_statuses.get(address),
                        fixture_available=normalized_submissions is not None,
                    )
                    expected = published[address]
                    gain_delta = computed_gain - expected.relative_gain
                    reward_matches = computed_reward == expected.wallet_reward
                    gain_matches = abs(gain_delta) <= gain_tolerance
                    raw_matches = gain_matches and reward_matches
                    caveats = (
                        caveats_for_context(
                            challenge=challenge,
                            competition=competition,
                            audit_kind="scoring",
                            address=address,
                        )
                        if not raw_matches
                        else []
                    )
                    caveated_pass = any(
                        caveat["counts_as_pass"] for caveat in caveats
                    )
                    comparisons.append(
                        {
                            "address": address,
                            "submission_status": status,
                            "computed_relative_gain": str(computed_gain),
                            "published_relative_gain": str(expected.relative_gain),
                            "relative_gain_delta": str(gain_delta),
                            "computed_wallet_reward": str(computed_reward),
                            "published_wallet_reward": str(expected.wallet_reward),
                            "relative_gain_matches": gain_matches,
                            "wallet_reward_matches": reward_matches,
                            "caveated_pass": caveated_pass,
                            "effective_match": raw_matches or caveated_pass,
                            "caveats": caveats,
                        }
                    )
                raw_mismatches = [
                    row
                    for row in comparisons
                    if not row["relative_gain_matches"] or not row["wallet_reward_matches"]
                ]
                caveated_comparisons = [
                    row for row in raw_mismatches if row["caveated_pass"]
                ]
                unresolved_mismatches = [
                    row for row in raw_mismatches if not row["caveated_pass"]
                ]
                max_gain_delta = max(
                    (abs(Decimal(row["relative_gain_delta"])) for row in comparisons),
                    default=Decimal(0),
                )
                report = {
                    "schema_version": 1,
                    "challenge": challenge,
                    "competition": competition,
                    "policy_id": policy.policy_id,
                    "policy_source_git_commit": policy.source_git_commit,
                    "policy_source_files_sha256": dict(
                        policy.source_files_sha256
                    ),
                    "policy_status": policy.status,
                    "reproduction_runtime": {
                        "python": platform.python_version(),
                        "pandas": version("pandas"),
                        "numpy": version("numpy"),
                    },
                    "result_cid": result_cid,
                    "resolved_result_cid": resolved_result_cid,
                    "result_bytes_sha256": result_artifact.sha256,
                    "gain_tolerance": str(gain_tolerance),
                    "participant_count": len(comparisons),
                    "mismatch_count": len(raw_mismatches),
                    "raw_mismatch_count": len(raw_mismatches),
                    "caveated_comparison_count": len(caveated_comparisons),
                    "unresolved_mismatch_count": len(unresolved_mismatches),
                    "maximum_absolute_gain_delta": str(max_gain_delta),
                    "raw_passed": not raw_mismatches,
                    "passed": not unresolved_mismatches,
                    "participants": comparisons,
                }
                report_caveats = {
                    caveat["id"]: caveat
                    for caveat in caveats_for_context(
                        challenge=challenge,
                        competition=competition,
                        audit_kind="scoring",
                    )
                } | {
                    caveat["id"]: caveat
                    for caveat in publication_report.get("caveats", [])
                } | {
                    caveat["id"]: caveat
                    for row in raw_mismatches
                    for caveat in row["caveats"]
                }
                if report_caveats:
                    report["caveats"] = list(report_caveats.values())
                if caveated_comparisons:
                    report["passed_with_caveat"] = report["passed"]
                destination = (
                    self.root
                    / "reports"
                    / "scoring"
                    / f"challenge-{challenge:03d}-{competition.lower()}.json"
                )
                write_canonical_json(destination, report)
                reports.append(report)
        return reports

    def audit_correction_40_42(
        self, *, progress: ProgressCallback | None = None
    ) -> list[dict[str, Any]]:
        """Verify challenge 40 mistake, challenge 41 undo, and challenge 42 fix."""

        manifests = {
            manifest["challenge"]: manifest
            for manifest in self._chain_manifests(range(40, 43))
        }
        if set(manifests) != {40, 41, 42}:
            raise ValueError("correction audit requires challenges 40, 41, and 42")
        returns = read_realized_returns(
            self.root / "data" / "prices" / "challenge-040.csv",
            binary_float=True,
        )
        reports = []
        for competition, observed40 in manifests[40]["competitions"].items():
            key_cid = observed40["content"]["private_key"]["cid"]
            private_key = self.ipfs.download(key_cid, progress=progress).path
            predictions: dict[str, dict[str, Decimal]] = {}
            participant_evidence = []
            statuses = {}
            for participant in observed40["participants"]:
                address = participant["address"]
                submission = participant["submission"]
                if submission is None:
                    statuses[address] = "no-submission"
                    continue
                base = {"address": address, "submission_cid": submission["cid"]}
                try:
                    archive = self.ipfs.download(
                        submission["cid"], progress=progress
                    )
                    decrypted = decrypt_submission_archive(
                        archive.path, private_key, address
                    )
                    values = parse_predictions(
                        decrypted.predictions_csv,
                        LEGACY_30_CANDIDATE.symbols,
                        reject_duplicates=True,
                    )
                    predictions[address] = values
                    evidence = {
                        **base,
                        "status": "valid",
                        "archive_sha256": archive.sha256,
                        "predictions_sha256": hashlib.sha256(
                            decrypted.predictions_csv
                        ).hexdigest(),
                        "prediction_count": len(values),
                    }
                    participant_evidence.append(evidence)
                    statuses[address] = "valid"
                except (
                    InvalidSubmission,
                    IpfsDownloadError,
                    zipfile.BadZipFile,
                    OSError,
                ) as error:
                    statuses[address] = f"invalid: {error}"

            fixture_path = (
                self.root
                / "data"
                / "submissions"
                / f"correction-040-042-{competition.lower()}.csv"
            )
            fixture = write_submission_fixture(
                fixture_path,
                challenge=42,
                competition=competition,
                policy=LEGACY_30_CANDIDATE,
                predictions=predictions,
                participant_evidence=participant_evidence,
            )
            observed42 = manifests[42]["competitions"][competition]
            result_cid = observed42["content"]["results"]["cid"]
            result_artifact = self.ipfs.download(result_cid, progress=progress)
            published = read_published_results(
                result_artifact.path,
                competition=competition,
                challenge=40,
            )
            report = audit_correction_sequence(
                competition=competition,
                manifests=manifests,
                published=published,
                predictions=predictions,
                submission_statuses=statuses,
                realized_returns=returns,
            )
            report.update(
                {
                    "policy_id": LEGACY_30_CANDIDATE.policy_id,
                    "policy_source_git_commit": LEGACY_30_CANDIDATE.source_git_commit,
                    "policy_source_files_sha256": dict(
                        LEGACY_30_CANDIDATE.source_files_sha256
                    ),
                    "challenge_40_private_key_cid": key_cid,
                    "corrected_result_cid": result_cid,
                    "corrected_result_bytes_sha256": result_artifact.sha256,
                    "normalized_fixture": fixture,
                    "collector_reference": {
                        "description": "Provided historical export logic unions challenge-40 submitters into challenges 41 and 42.",
                        "provided_file_sha256": "cba7659bc0de0bcd1e7aec2e81d03df6c0a9200eb8138818108f673497a7c0c5",
                    },
                }
            )
            write_canonical_json(
                self._correction_sequence_path(competition), report
            )
            reports.append(report)
        return reports

    def derive_prices_from_targets(
        self, *, challenges: range
    ) -> list[dict[str, Any]]:
        """Build the exact legacy scoring basket from verified target fixtures."""

        reports = []
        for challenge in challenges:
            policy = self._effective_policy(challenge)
            source = (
                self.root / "data" / "targets" / f"challenge-{challenge:03d}.csv"
            )
            competitions = (
                (("UPDOWN", "target_updown"), ("NEUTRAL", "target_neutral"))
                if self._is_dynamic_policy(policy)
                else ((None, "target_updown"),)
            )
            for competition, target_column in competitions:
                reports.append(
                    derive_price_fixture_from_targets(
                        source,
                        symbols=policy.symbols,
                        policy_id=policy.policy_id,
                        destination=self._price_fixture_path(challenge, competition),
                        target_column=target_column,
                        source_reference=str(source.relative_to(self.root)),
                        require_all_symbols=True,
                    )
                )
        return reports

    def _score_participant(
        self,
        challenge: int,
        competition: str,
        address: str,
        submission: dict[str, Any] | None,
        stake: Decimal,
        returns: dict[str, Decimal],
        policy: ScoringPolicy,
        normalized_prediction: dict[str, Decimal] | None = None,
        ingestion_status: str | None = None,
        fixture_available: bool = False,
    ) -> tuple[Decimal, Decimal, str]:
        if not submission:
            return Decimal(0), Decimal(0), "no-submission"
        if fixture_available:
            if normalized_prediction is None:
                return Decimal(0), Decimal(0), ingestion_status or "invalid"
            predictions = normalized_prediction
            status = "valid"
        else:
            path = (
                self.root
                / ".cache"
                / "decrypted"
                / f"challenge-{challenge:03d}"
                / competition.lower()
                / f"{address}.csv"
            )
            if not path.exists():
                return Decimal(0), Decimal(0), "not-decrypted"
            try:
                predictions, _ = self._parse_submission(path.read_bytes(), policy)
                status = "valid"
            except (InvalidSubmission, ValueError, ArithmeticError) as error:
                return Decimal(0), Decimal(0), f"invalid: {error}"
        try:
            predictions = {
                symbol: value
                for symbol, value in predictions.items()
                if symbol in returns
            }
            if not predictions:
                raise InvalidSubmission("no submitted symbols have realized targets")
            if (
                self._is_dynamic_policy(policy)
                and competition == "NEUTRAL"
                and len(predictions) < 2
            ):
                raise InvalidSubmission("NEUTRAL overlap below 2 symbols")
            gain, reward = score_prediction(
                competition,
                predictions,
                returns,
                stake,
                reward_digits=policy.reward_digits,
            )
            return gain, reward, status
        except (InvalidSubmission, ValueError, ArithmeticError) as error:
            return Decimal(0), Decimal(0), f"invalid: {error}"

    def _decrypt_one_submission(
        self,
        challenge: int,
        competition: str,
        address: str,
        submission_cid: str,
        private_key: Path,
    ) -> dict[str, Any]:
        base = {
            "address": address,
            "submission_cid": submission_cid,
        }
        try:
            policy = self._effective_policy(challenge)
            archive = self.ipfs.download(submission_cid)
            decrypted = decrypt_submission_archive(archive.path, private_key, address)
            predictions, diagnostics = self._parse_submission(
                decrypted.predictions_csv, policy
            )
            destination = (
                self.root
                / ".cache"
                / "decrypted"
                / f"challenge-{challenge:03d}"
                / competition.lower()
                / f"{address}.csv"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(decrypted.predictions_csv)
            return {
                **base,
                "status": "valid",
                "archive_sha256": archive.sha256,
                "predictions_sha256": hashlib.sha256(
                    decrypted.predictions_csv
                ).hexdigest(),
                "prediction_count": len(predictions),
                **diagnostics,
                "prediction_member": decrypted.prediction_member,
                "key_member": decrypted.key_member,
            }
        except (
            InvalidSubmission,
            IpfsDownloadError,
            zipfile.BadZipFile,
            OSError,
        ) as error:
            return {**base, "status": "invalid", "problem": str(error)}

    def _submission_fixture_path(self, challenge: int, competition: str) -> Path:
        return (
            self.root
            / "data"
            / "submissions"
            / f"challenge-{challenge:03d}-{competition.lower()}.csv"
        )

    def _correction_sequence_path(self, competition: str) -> Path:
        return (
            self.root
            / "reports"
            / "corrections"
            / f"challenges-040-042-{competition.lower()}.json"
        )

    def _correction_sequence_report(
        self, challenge: int, competition: str
    ) -> dict[str, Any] | None:
        if challenge not in {41, 42}:
            return None
        path = self._correction_sequence_path(competition)
        if not path.exists():
            return None
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("sequence") != [40, 41, 42] or not report.get("passed"):
            raise ValueError(f"invalid correction-sequence report: {path}")
        return report

    def _correction_publication_report(
        self,
        manifest: dict[str, Any],
        competition: str,
        observed: dict[str, Any],
        special: dict[str, Any],
    ) -> dict[str, Any]:
        challenge = manifest["challenge"]
        phase = "undo" if challenge == 41 else "corrected-settlement"
        return {
            "schema_version": 1,
            "challenge": challenge,
            "competition": competition,
            "contract": observed["contract"],
            "observed_block": manifest["observed_block"],
            "result_cid": observed["content"]["results"]["cid"],
            "result_bytes_sha256": special["corrected_result_bytes_sha256"],
            "raw_primary_reference_passed": False,
            "raw_problem": (
                "result CSV embeds challenge 40 and is not a standalone challenge-41 publication"
                if challenge == 41
                else "corrected result CSV intentionally embeds original challenge 40"
            ),
            "resolution": "accepted-challenges-40-42-correction-sequence",
            "correction_phase": phase,
            "mismatch_count": 1,
            "raw_passed": False,
            "passed_with_caveat": True,
            "passed": True,
            "correction_report": str(
                self._correction_sequence_path(competition).relative_to(self.root)
            ),
            "caveats": caveats_for_context(
                challenge=challenge,
                competition=competition,
                audit_kind="publication",
            ),
        }

    def _correction_scoring_report(
        self,
        manifest: dict[str, Any],
        competition: str,
        observed: dict[str, Any],
        special: dict[str, Any],
    ) -> dict[str, Any]:
        challenge = manifest["challenge"]
        undo = challenge == 41
        mismatch_count = (
            special["undo_mismatch_count"]
            if undo
            else special["corrected_mismatch_count"]
        )
        return {
            "schema_version": 1,
            "challenge": challenge,
            "competition": competition,
            "policy_id": special["policy_id"],
            "policy_source_git_commit": special["policy_source_git_commit"],
            "policy_source_files_sha256": special["policy_source_files_sha256"],
            "policy_status": "verified-by-accepted-correction-sequence",
            "result_cid": observed["content"]["results"]["cid"],
            "result_bytes_sha256": special["corrected_result_bytes_sha256"],
            "audit_status": (
                "accepted-exact-undo" if undo else "accepted-corrected-settlement"
            ),
            "participant_count": special["comparison_count"],
            "comparison_count": special["comparison_count"],
            "mismatch_count": mismatch_count,
            "raw_mismatch_count": mismatch_count,
            "unresolved_mismatch_count": 0,
            "raw_passed": mismatch_count == 0,
            "passed_with_caveat": True,
            "passed": mismatch_count == 0,
            "correction_report": str(
                self._correction_sequence_path(competition).relative_to(self.root)
            ),
            "caveats": caveats_for_context(
                challenge=challenge,
                competition=competition,
                audit_kind="scoring",
            ),
            "participants": special["comparisons"],
        }

    def _price_fixture_path(
        self, challenge: int, competition: str | None = None
    ) -> Path:
        policy = self._effective_policy(challenge)
        suffix = (
            f"-{str(competition).lower()}"
            if self._is_dynamic_policy(policy)
            else ""
        )
        return self.root / "data" / "prices" / f"challenge-{challenge:03d}{suffix}.csv"

    def _effective_policy(self, challenge: int) -> ScoringPolicy:
        policy = policy_for_challenge(challenge)
        if not self._is_dynamic_policy(policy):
            return policy
        provenance_path = (
            self.root / "data" / "evaluation" / f"challenge-{challenge:03d}.json"
        )
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        symbols = tuple(provenance["evaluation_symbols"])
        if not symbols or not set(symbols) <= set(policy.symbols):
            raise ValueError(
                f"invalid dynamic evaluation symbols for challenge {challenge}"
            )
        return replace(policy, symbols=symbols)

    @staticmethod
    def _is_dynamic_policy(policy: ScoringPolicy) -> bool:
        return policy.policy_id == "dynamic-evaluation-153-v1"

    def _parse_submission(
        self, predictions_csv: bytes, policy: ScoringPolicy
    ) -> tuple[dict[str, Decimal], dict[str, Any]]:
        if self._is_dynamic_policy(policy):
            parsed = parse_dynamic_predictions(
                predictions_csv,
                policy.symbols,
                aliases=dict(DYNAMIC_SYMBOL_ALIASES),
            )
            return parsed.predictions, {
                "ignored_extra_symbols": list(parsed.extras),
                "dropped_duplicate_symbols": list(parsed.duplicates),
                "missing_evaluation_symbols": list(parsed.missing),
            }
        return (
            parse_predictions(
                predictions_csv, policy.symbols, reject_duplicates=True
            ),
            {},
        )

    def _write_submission_fixture(
        self,
        challenge: int,
        competition: str,
        policy: ScoringPolicy,
        participants: list[dict[str, Any]],
    ) -> dict[str, Any]:
        normalized: dict[str, dict[str, Decimal]] = {}
        for participant in participants:
            if participant["status"] != "valid":
                continue
            address = participant["address"]
            source = (
                self.root
                / ".cache"
                / "decrypted"
                / f"challenge-{challenge:03d}"
                / competition.lower()
                / f"{address}.csv"
            )
            normalized[address], _ = self._parse_submission(source.read_bytes(), policy)
        return write_submission_fixture(
            self._submission_fixture_path(challenge, competition),
            challenge=challenge,
            competition=competition,
            policy=policy,
            predictions=normalized,
            participant_evidence=participants,
            require_all_symbols=not self._is_dynamic_policy(policy),
        )

    def extract_prices(
        self,
        *,
        progress: ProgressCallback | None = None,
        challenges: range | None = None,
    ) -> list[Path]:
        catalog = self._dataset_catalog_by_challenge()
        written = []
        selected = (
            range(FIRST_CHALLENGE, LAST_CHALLENGE + 1)
            if challenges is None
            else challenges
        )
        for challenge in selected:
            policy = self._effective_policy(challenge)
            source_challenge = challenge + 1
            source_cid = catalog[source_challenge]["dataset"]["cid"]
            artifact = self.ipfs.download(source_cid, progress=progress)
            prices, member = extract_latest_realized_returns(
                artifact.path,
                scoring_challenge=challenge,
                source_dataset_challenge=source_challenge,
                source_cid=source_cid,
                symbols=policy.symbols,
            )
            destination = self.root / "data" / "prices" / f"challenge-{challenge:03d}.csv"
            write_price_fixture(prices, member, artifact.sha256, destination)
            written.append(destination)
        return written

    def verify_prices(
        self,
        *,
        progress: ProgressCallback | None = None,
        challenges: range | None = None,
    ) -> dict[str, Any]:
        catalog = self._dataset_catalog_by_challenge()
        selected = (
            range(FIRST_CHALLENGE, LAST_CHALLENGE + 1)
            if challenges is None
            else challenges
        )
        comparisons = []
        for challenge in selected:
            policy = self._effective_policy(challenge)
            source_challenge = challenge + 1
            source_cid = catalog[source_challenge]["dataset"]["cid"]
            artifact = self.ipfs.download(source_cid, progress=progress)
            prices, member = extract_latest_realized_returns(
                artifact.path,
                scoring_challenge=challenge,
                source_dataset_challenge=source_challenge,
                source_cid=source_cid,
                symbols=policy.symbols,
            )
            destination = self.root / "data" / "prices" / f"challenge-{challenge:03d}.csv"
            problem = None
            try:
                verify_price_fixture(prices, member, artifact.sha256, destination)
            except (FileNotFoundError, ValueError) as error:
                problem = str(error)
            comparisons.append(
                {
                    "challenge": challenge,
                    "source_dataset_challenge": source_challenge,
                    "source_cid": source_cid,
                    "source_archive_sha256": artifact.sha256,
                    "price_fixture_sha256": (
                        hashlib.sha256(destination.read_bytes()).hexdigest()
                        if destination.exists()
                        else None
                    ),
                    "passed": problem is None,
                    "problem": problem,
                }
            )
        report = {
            "schema_version": 1,
            "comparison_count": len(comparisons),
            "mismatch_count": sum(not item["passed"] for item in comparisons),
            "passed": all(item["passed"] for item in comparisons),
            "comparisons": comparisons,
        }
        write_canonical_json(
            self.root / "reports" / "prices" / "verification.json",
            report,
        )
        return report

    def build_summary(self) -> dict[str, Any]:
        """Build the compact first-ten audit summary from detailed reports."""

        return build_first_ten_summary(
            self.root,
            self.root / "reports" / "first-ten-summary.json",
        )

    def build_audit_status(self) -> dict[str, Any]:
        """Build the repository-wide audit status from detailed reports."""

        return build_audit_status(
            self.root,
            self.root / "reports" / "audit-status.json",
        )

    def _dataset_catalog(self) -> dict[str, Any]:
        path = self.root / "manifests" / "datasets.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _dataset_catalog_by_challenge(self) -> dict[int, dict[str, Any]]:
        return {
            row["challenge"]: row for row in self._dataset_catalog()["datasets"]
        }

    def _chain_manifests(
        self, challenges: range | None = None
    ) -> list[dict[str, Any]]:
        selected = set(
            range(FIRST_CHALLENGE, LAST_CHALLENGE + 1)
            if challenges is None
            else challenges
        )
        manifests = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((self.root / "manifests" / "chain").glob("*.json"))
        ]
        return [manifest for manifest in manifests if manifest["challenge"] in selected]

    def _download_submission_scope(
        self,
        challenges: range | None,
        progress: ProgressCallback | None,
    ) -> list[DownloadedArtifact]:
        cids: set[str] = set()
        for manifest in self._chain_manifests(challenges):
            for competition in manifest["competitions"].values():
                for participant in competition["participants"]:
                    submission = participant["submission"]
                    if submission and submission["cid"]:
                        cids.add(submission["cid"])
        return self.ipfs.download_many(cids, progress=progress)

    def _content_cids(
        self, field: str, challenges: range | None = None
    ) -> set[str]:
        cids: set[str] = set()
        for manifest in self._chain_manifests(challenges):
            for competition in manifest["competitions"].values():
                cid = competition["content"][field]["cid"]
                if cid:
                    cids.add(cid)
        return cids
