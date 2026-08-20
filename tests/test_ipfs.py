import hashlib
import json
from pathlib import Path

import pytest

from comp_verification.encoding import single_block_file_cid_v0
from comp_verification.ipfs import DownloadedArtifact, IpfsDownloadError, IpfsGateway


class OfflineGateway(IpfsGateway):
    def _remote_size(self, cid: str) -> int:
        raise AssertionError("verified cached evidence must not require the gateway")


class PartiallyUnavailableGateway(IpfsGateway):
    def download(self, cid: str, **kwargs) -> DownloadedArtifact:
        if cid == "bad":
            raise IpfsDownloadError("failed to download bad")
        path = self.cache / cid
        return DownloadedArtifact(cid, path, 1, "digest")


def test_recorded_hash_can_adopt_an_unmarked_cached_file(tmp_path: Path) -> None:
    payload = b"previously downloaded result evidence"
    cid = single_block_file_cid_v0(payload)
    cache = tmp_path / "ipfs"
    cache.mkdir()
    (cache / cid).write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    gateway = OfflineGateway("https://ipfs.example/ipfs", cache)

    artifact = gateway.download(cid, expected_sha256=expected)

    assert artifact.sha256 == expected
    assert (cache / f"{cid}.complete").exists()


def test_prune_verified_artifact_removes_only_file_and_marker(tmp_path: Path) -> None:
    payload = b"verified dataset"
    cid = single_block_file_cid_v0(payload)
    cache = tmp_path / "ipfs"
    cache.mkdir()
    path = cache / cid
    marker = cache / f"{cid}.complete"
    unrelated = cache / "keep-me"
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    marker.write_text(
        json.dumps(
            {"sha256": digest, "size": len(payload)},
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="ascii",
    )
    unrelated.write_bytes(b"unrelated")
    gateway = OfflineGateway("https://ipfs.example/ipfs", cache)
    artifact = gateway.download(cid, expected_sha256=digest)

    gateway.prune_verified_artifact(artifact)

    assert not path.exists()
    assert not marker.exists()
    assert unrelated.read_bytes() == b"unrelated"


def test_prune_refuses_changed_marker_and_keeps_raw_bytes(tmp_path: Path) -> None:
    payload = b"verified dataset"
    cid = single_block_file_cid_v0(payload)
    cache = tmp_path / "ipfs"
    cache.mkdir()
    path = cache / cid
    marker = cache / f"{cid}.complete"
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    marker.write_text(
        json.dumps({"sha256": "wrong", "size": len(payload)}), encoding="ascii"
    )
    artifact = DownloadedArtifact(cid, path, len(payload), digest)
    gateway = OfflineGateway("https://ipfs.example/ipfs", cache)

    with pytest.raises(IpfsDownloadError, match="marker"):
        gateway.prune_verified_artifact(artifact)

    assert path.exists()
    assert marker.exists()


def test_prune_accepts_legacy_size_marker_after_hash_and_cid_checks(
    tmp_path: Path,
) -> None:
    payload = b"legacy verified dataset"
    cid = single_block_file_cid_v0(payload)
    cache = tmp_path / "ipfs"
    cache.mkdir()
    path = cache / cid
    marker = cache / f"{cid}.complete"
    path.write_bytes(payload)
    marker.write_text(str(len(payload)), encoding="ascii")
    artifact = DownloadedArtifact(
        cid, path, len(payload), hashlib.sha256(payload).hexdigest()
    )

    OfflineGateway("https://ipfs.example/ipfs", cache).prune_verified_artifact(artifact)

    assert not path.exists()
    assert not marker.exists()


def test_authenticated_gateway_uses_pinata_token_query(
    tmp_path: Path,
) -> None:
    gateway = OfflineGateway(
        "https://private.example/ipfs",
        tmp_path,
        gateway_token="secret token",
    )

    assert gateway._artifact_url("QmCid") == (
        "https://private.example/ipfs/QmCid?pinataGatewayToken=secret+token"
    )
    assert "X-Pinata-Gateway-Token" not in gateway._request_headers()


def test_best_effort_download_retains_individual_failures(tmp_path: Path) -> None:
    gateway = PartiallyUnavailableGateway("https://ipfs.example/ipfs", tmp_path)

    artifacts, failures = gateway.download_many_best_effort({"good", "bad"})

    assert [artifact.cid for artifact in artifacts] == ["good"]
    assert failures == {"bad": "failed to download bad"}
