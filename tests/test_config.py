from pathlib import Path

import pytest

from comp_verification.config import ScopeConfig, VerifierConfig


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
    assert config.scope.chain_challenges == range(1, 11)
    assert config.scope.dataset_challenges == range(1, 12)


def test_scope_separates_chain_dataset_and_score_ready_bounds(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
[rpc]
url = "https://polygon.example"

[ipfs]
gateway_url = "https://ipfs.example/ipfs"

[scope]
first_challenge = 1
last_challenge = 173
last_dataset_challenge = 173
""".strip(),
        encoding="utf-8",
    )

    scope = VerifierConfig.load(path).scope

    assert scope.chain_challenges == range(1, 174)
    assert scope.dataset_challenges == range(1, 174)
    assert scope.score_ready_challenges == range(1, 173)


def test_scope_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError, match="last_challenge"):
        ScopeConfig(first_challenge=2, last_challenge=1).validate()
