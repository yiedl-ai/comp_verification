import hashlib
import io
import json
from pathlib import Path
from urllib.error import URLError

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


def test_large_download_uses_bounded_resumable_ranges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"abcdefghij"
    requested_ranges: list[str] = []

    class Response(io.BytesIO):
        status = 206

        def __init__(self, data: bytes, start: int, end: int) -> None:
            super().__init__(data)
            self.headers = {
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{len(payload)}",
            }

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        value = request.get_header("Range")
        requested_ranges.append(value)
        start_text, end_text = value.removeprefix("bytes=").split("-", 1)
        start = int(start_text)
        end = min(int(end_text), len(payload) - 1)
        return Response(payload[start : end + 1], start, end)

    monkeypatch.setattr("comp_verification.ipfs.urlopen", fake_urlopen)
    partial = tmp_path / "artifact.part"
    gateway = IpfsGateway(
        "https://ipfs.example/ipfs",
        tmp_path,
        chunk_size=2,
        range_request_bytes=4,
    )

    gateway._download_to_partial("QmCid", partial, progress=None)

    assert partial.read_bytes() == payload
    assert requested_ranges == ["bytes=0-3", "bytes=4-7", "bytes=8-11"]


def test_zero_length_head_and_hanging_range_falls_back_to_plain_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"historical submission archive"
    cid = single_block_file_cid_v0(payload)
    requests: list[tuple[str, str | None]] = []

    class Response(io.BytesIO):
        status = 200

        def __init__(self, data: bytes, content_length: int) -> None:
            super().__init__(data)
            self.headers = {"Content-Length": str(content_length)}

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        method = request.get_method()
        range_value = request.get_header("Range")
        requests.append((method, range_value))
        if method == "HEAD":
            return Response(b"", 0)
        if range_value is not None:
            raise URLError("gateway range request stalled")
        return Response(payload, len(payload))

    monkeypatch.setattr("comp_verification.ipfs.urlopen", fake_urlopen)
    gateway = IpfsGateway(
        "https://ipfs.example/ipfs",
        tmp_path,
        attempts=1,
        max_concurrent_ranges_per_download=1,
    )

    artifact = gateway.download(cid)

    assert artifact.path.read_bytes() == payload
    assert requests == [
        ("GET", "bytes=0-16777215"),
        ("HEAD", None),
        ("GET", None),
    ]


def test_concurrent_ranges_reuse_retained_segments_and_assemble(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"abcdefghij"
    requested_ranges: list[str] = []

    class Response(io.BytesIO):
        status = 206

        def __init__(self, data: bytes, headers: dict[str, str]) -> None:
            super().__init__(data)
            self.headers = headers

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        if request.get_method() == "HEAD":
            return Response(b"", {"Content-Length": str(len(payload))})
        value = request.get_header("Range")
        requested_ranges.append(value)
        start_text, end_text = value.removeprefix("bytes=").split("-", 1)
        start, end = int(start_text), int(end_text)
        data = payload[start : end + 1]
        return Response(
            data,
            {
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{len(payload)}",
            },
        )

    monkeypatch.setattr("comp_verification.ipfs.urlopen", fake_urlopen)
    partial = tmp_path / "QmCid.part"
    partial.write_bytes(payload[:2])
    retained = tmp_path / ".ranges" / "QmCid" / "2-5.part"
    retained.parent.mkdir(parents=True)
    retained.write_bytes(payload[2:6])
    gateway = IpfsGateway(
        "https://ipfs.example/ipfs",
        tmp_path,
        chunk_size=2,
        range_request_bytes=4,
        max_concurrent_ranges_per_download=2,
    )

    gateway._download_to_partial_concurrently("QmCid", partial, progress=None)

    assert partial.read_bytes() == payload
    assert requested_ranges == ["bytes=6-9"]
    assert not (tmp_path / ".ranges").exists()
