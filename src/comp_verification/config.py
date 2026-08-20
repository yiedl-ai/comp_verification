"""Typed TOML configuration for network and download behavior."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RpcConfig:
    url: str
    timeout_seconds: float = 45.0
    attempts: int = 5
    retry_base_delay_seconds: float = 1.0
    json_batch_size: int = 100
    json_batch_interval_seconds: float = 1.1
    multicall_batch_size: int = 100
    log_block_span: int = 10_000

    def validate(self) -> None:
        if not self.url.startswith(("http://", "https://")):
            raise ValueError("rpc.url must be an HTTP(S) URL")
        _positive("rpc.timeout_seconds", self.timeout_seconds)
        _positive("rpc.attempts", self.attempts)
        _positive("rpc.retry_base_delay_seconds", self.retry_base_delay_seconds)
        _positive("rpc.json_batch_size", self.json_batch_size)
        _positive("rpc.json_batch_interval_seconds", self.json_batch_interval_seconds)
        _positive("rpc.multicall_batch_size", self.multicall_batch_size)
        _positive("rpc.log_block_span", self.log_block_span)


@dataclass(frozen=True)
class IpfsConfig:
    gateway_url: str
    gateway_token: str | None = None
    user_agent: str = "comp-verification/0.1"
    timeout_seconds: float = 120.0
    attempts: int = 5
    retry_base_delay_seconds: float = 2.0
    chunk_size_bytes: int = 1024 * 1024
    range_request_bytes: int = 16 * 1024 * 1024
    max_concurrent_downloads: int = 8

    def validate(self) -> None:
        if not self.gateway_url.startswith(("http://", "https://")):
            raise ValueError("ipfs.gateway_url must be an HTTP(S) URL")
        if not self.user_agent.strip():
            raise ValueError("ipfs.user_agent must not be empty")
        _positive("ipfs.timeout_seconds", self.timeout_seconds)
        _positive("ipfs.attempts", self.attempts)
        _positive("ipfs.retry_base_delay_seconds", self.retry_base_delay_seconds)
        _positive("ipfs.chunk_size_bytes", self.chunk_size_bytes)
        _positive("ipfs.range_request_bytes", self.range_request_bytes)
        _positive("ipfs.max_concurrent_downloads", self.max_concurrent_downloads)


@dataclass(frozen=True)
class ScopeConfig:
    """Inclusive bounds for evidence collection and score-ready datasets."""

    first_challenge: int = 1
    last_challenge: int = 10
    last_dataset_challenge: int = 11

    def validate(self) -> None:
        _positive("scope.first_challenge", self.first_challenge)
        _positive("scope.last_challenge", self.last_challenge)
        _positive("scope.last_dataset_challenge", self.last_dataset_challenge)
        if self.last_challenge < self.first_challenge:
            raise ValueError("scope.last_challenge must not precede first_challenge")
        if self.last_dataset_challenge < self.first_challenge:
            raise ValueError(
                "scope.last_dataset_challenge must not precede first_challenge"
            )

    @property
    def chain_challenges(self) -> range:
        return range(self.first_challenge, self.last_challenge + 1)

    @property
    def dataset_challenges(self) -> range:
        return range(self.first_challenge, self.last_dataset_challenge + 1)

    @property
    def score_ready_challenges(self) -> range:
        last = min(self.last_challenge, self.last_dataset_challenge - 1)
        return range(self.first_challenge, last + 1)


@dataclass(frozen=True)
class VerifierConfig:
    rpc: RpcConfig
    ipfs: IpfsConfig
    scope: ScopeConfig = ScopeConfig()

    @classmethod
    def load(cls, path: Path) -> "VerifierConfig":
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
        config = cls(
            rpc=RpcConfig(**_table(raw, "rpc")),
            ipfs=IpfsConfig(**_table(raw, "ipfs")),
            scope=ScopeConfig(**raw.get("scope", {})),
        )
        config.rpc.validate()
        config.ipfs.validate()
        config.scope.validate()
        return config


def _table(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"missing [{name}] table")
    return value


def _positive(name: str, value: int | float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")
