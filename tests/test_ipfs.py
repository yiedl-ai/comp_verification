import hashlib
from pathlib import Path

from comp_verification.encoding import single_block_file_cid_v0
from comp_verification.ipfs import IpfsGateway


class OfflineGateway(IpfsGateway):
    def _remote_size(self, cid: str) -> int:
        raise AssertionError("verified cached evidence must not require the gateway")


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
