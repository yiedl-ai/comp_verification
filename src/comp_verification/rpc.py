"""Minimal Polygon JSON-RPC client and competition contract reader."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from eth_abi import decode as abi_decode
from eth_abi import encode as abi_encode

from .encoding import (
    decode_address_array,
    decode_bytes32,
    decode_uint,
    encode_address,
    encode_call,
    encode_uint,
    function_selector,
)

T = TypeVar("T")


class RpcError(RuntimeError):
    """Raised when Polygon returns an RPC error or an invalid response."""


class RpcResponseTooLarge(RpcError):
    """Raised when the provider refuses an oversized response."""


@dataclass(frozen=True)
class ContractCall:
    to: str
    data: str


class PolygonRpc:
    def __init__(
        self,
        url: str,
        *,
        timeout: float = 45,
        attempts: int = 5,
        retry_base_delay: float = 1.0,
        json_batch_size: int = 100,
        json_batch_interval: float = 1.1,
        multicall_batch_size: int = 100,
        log_block_span: int = 10_000,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.attempts = attempts
        self.retry_base_delay = retry_base_delay
        self.json_batch_size = json_batch_size
        self.json_batch_interval = json_batch_interval
        self.multicall_batch_size = multicall_batch_size
        self.log_block_span = log_block_span
        self._request_id = 0

    def _post(self, payload: Any) -> Any:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(self.attempts):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.load(response)
            except HTTPError as error:
                if error.code == 413:
                    raise RpcResponseTooLarge("RPC response exceeded provider limit") from error
                last_error = error
                if attempt + 1 < self.attempts:
                    time.sleep(self.retry_base_delay * 2**attempt)
            except (URLError, TimeoutError, json.JSONDecodeError) as error:
                last_error = error
                if attempt + 1 < self.attempts:
                    time.sleep(self.retry_base_delay * 2**attempt)
        raise RpcError(f"RPC request failed after {self.attempts} attempts") from last_error

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def chain_id(self) -> int:
        request_id = self._next_id()
        response = self._post(
            {"jsonrpc": "2.0", "id": request_id, "method": "eth_chainId", "params": []}
        )
        return decode_uint(self._unwrap(response, request_id))

    def block_number(self) -> int:
        request_id = self._next_id()
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "eth_blockNumber",
                "params": [],
            }
        )
        return decode_uint(self._unwrap(response, request_id))

    def get_logs(
        self,
        addresses: str | list[str],
        from_block: int,
        to_block: int,
        *,
        topic0: list[str] | None = None,
        block_span: int | None = None,
    ) -> list[dict[str, Any]]:
        """Read logs in configurable spans to stay within provider limits."""

        if from_block < 0 or to_block < from_block:
            raise ValueError("invalid log block range")
        span = self.log_block_span if block_span is None else block_span
        if span <= 0:
            raise ValueError("log block span must be positive")
        output: list[dict[str, Any]] = []
        for start in range(from_block, to_block + 1, span):
            end = min(start + span - 1, to_block)
            output.extend(self._get_logs_range(addresses, start, end, topic0))
        return output

    def _get_logs_range(
        self,
        addresses: str | list[str],
        start: int,
        end: int,
        topic0: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Read one range, bisecting automatically when its response is too large."""

        request_id = self._next_id()
        parameters: dict[str, Any] = {
            "address": addresses,
            "fromBlock": hex(start),
            "toBlock": hex(end),
        }
        if topic0:
            parameters["topics"] = [topic0]
        try:
            response = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "eth_getLogs",
                    "params": [parameters],
                }
            )
        except RpcResponseTooLarge:
            if start == end:
                raise
            middle = (start + end) // 2
            return self._get_logs_range(
                addresses, start, middle, topic0
            ) + self._get_logs_range(addresses, middle + 1, end, topic0)
        result = self._unwrap_value(response, request_id)
        if not isinstance(result, list) or not all(
            isinstance(item, dict) for item in result
        ):
            raise RpcError("invalid eth_getLogs result")
        return result

    def call(self, call: ContractCall, block: str = "latest") -> str:
        request_id = self._next_id()
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "eth_call",
                "params": [{"to": call.to, "data": call.data}, block],
            }
        )
        return self._unwrap(response, request_id)

    def batch_call(
        self,
        calls: Iterable[ContractCall],
        *,
        block: str = "latest",
        batch_size: int | None = None,
        batch_interval: float | None = None,
    ) -> list[str]:
        pending = list(calls)
        output: list[str] = []
        batch_size = self.json_batch_size if batch_size is None else batch_size
        batch_interval = (
            self.json_batch_interval if batch_interval is None else batch_interval
        )
        starts = range(0, len(pending), batch_size)
        for start in starts:
            # Batch members count individually against provider request limits.
            # The pause also separates batches from the metadata calls before them.
            time.sleep(batch_interval)
            chunk = pending[start : start + batch_size]
            requests = []
            order = []
            for call in chunk:
                request_id = self._next_id()
                order.append(request_id)
                requests.append(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": "eth_call",
                        "params": [{"to": call.to, "data": call.data}, block],
                    }
                )
            responses = self._post(requests)
            if not isinstance(responses, list):
                raise RpcError("batch RPC response was not a list")
            by_id = {item.get("id"): item for item in responses}
            output.extend(self._unwrap(by_id[request_id], request_id) for request_id in order)
        return output

    def multicall(
        self,
        calls: Iterable[ContractCall],
        registry: str,
        *,
        block: str = "latest",
        batch_size: int | None = None,
    ) -> list[str]:
        """Execute calls through the deployed registry's contract-level batchCall."""

        pending = list(calls)
        output: list[str] = []
        batch_size = self.multicall_batch_size if batch_size is None else batch_size
        for start in range(0, len(pending), batch_size):
            chunk = pending[start : start + batch_size]
            encoded_arguments = abi_encode(
                ["address[]", "bytes[]"],
                [
                    [bytes.fromhex(call.to.removeprefix("0x")) for call in chunk],
                    [bytes.fromhex(call.data.removeprefix("0x")) for call in chunk],
                ],
            )
            data = function_selector("batchCall(address[],bytes[])") + encoded_arguments.hex()
            result = self.call(ContractCall(registry, data), block)
            decoded = abi_decode(["bytes[]"], bytes.fromhex(result.removeprefix("0x")))[0]
            if len(decoded) != len(chunk):
                raise RpcError(
                    f"multicall returned {len(decoded)} values for {len(chunk)} calls"
                )
            output.extend("0x" + value.hex() for value in decoded)
        return output

    @staticmethod
    def _unwrap(response: dict[str, Any], request_id: int) -> str:
        result = PolygonRpc._unwrap_value(response, request_id)
        if not isinstance(result, str) or not result.startswith("0x"):
            raise RpcError(f"invalid RPC result: {result!r}")
        return result

    @staticmethod
    def _unwrap_value(response: dict[str, Any], request_id: int) -> Any:
        if not isinstance(response, dict):
            raise RpcError(f"invalid RPC response: {response!r}")
        if response.get("id") != request_id:
            raise RpcError(f"unexpected RPC response id: {response.get('id')!r}")
        if "error" in response:
            raise RpcError(f"RPC error: {response['error']}")
        if "result" not in response:
            raise RpcError("RPC response has no result")
        return response["result"]


def bytes32_call(contract: str, signature: str, challenge: int) -> ContractCall:
    return ContractCall(contract, encode_call(signature, encode_uint(challenge)))


def uint_call(contract: str, signature: str, challenge: int) -> ContractCall:
    return ContractCall(contract, encode_call(signature, encode_uint(challenge)))


def participant_call(
    contract: str, signature: str, challenge: int, participant: str
) -> ContractCall:
    return ContractCall(
        contract,
        encode_call(signature, encode_uint(challenge), encode_address(participant)),
    )


def read_bytes32(
    rpc: PolygonRpc,
    contract: str,
    signature: str,
    challenge: int,
    *,
    block: str = "latest",
) -> str:
    return decode_bytes32(rpc.call(bytes32_call(contract, signature, challenge), block))


def read_uint(
    rpc: PolygonRpc,
    contract: str,
    signature: str,
    challenge: int,
    *,
    block: str = "latest",
) -> int:
    return decode_uint(rpc.call(uint_call(contract, signature, challenge), block))


def read_addresses(
    rpc: PolygonRpc,
    contract: str,
    signature: str,
    challenge: int,
    *,
    block: str = "latest",
) -> list[str]:
    result = rpc.call(
        ContractCall(contract, encode_call(signature, encode_uint(challenge))), block
    )
    return decode_address_array(result)


def decode_many(results: Iterable[str], decoder: Callable[[str], T]) -> list[T]:
    return [decoder(result) for result in results]
