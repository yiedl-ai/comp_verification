from pathlib import Path

from comp_verification.config import VerifierConfig


def test_load_config(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
[rpc]
url = "https://polygon.example"
multicall_batch_size = 42

[ipfs]
gateway_url = "https://ipfs.example/ipfs"
chunk_size_bytes = 2048
""".strip(),
        encoding="utf-8",
    )

    config = VerifierConfig.load(path)

    assert config.rpc.multicall_batch_size == 42
    assert config.rpc.log_block_span == 10_000
    assert config.rpc.attempts == 5
    assert config.ipfs.chunk_size_bytes == 2048
    assert config.ipfs.user_agent == "comp-verification/0.1"
    assert config.ipfs.max_concurrent_downloads == 8
