from typing import Any

from comp_verification.rpc import PolygonRpc, RpcResponseTooLarge


class SplittingRpc(PolygonRpc):
    def __init__(self) -> None:
        super().__init__("https://polygon.example", log_block_span=10)
        self.ranges: list[tuple[int, int]] = []

    def _post(self, payload: Any) -> Any:
        parameters = payload["params"][0]
        start = int(parameters["fromBlock"], 16)
        end = int(parameters["toBlock"], 16)
        self.ranges.append((start, end))
        if end - start + 1 > 2:
            raise RpcResponseTooLarge("test limit")
        return {"jsonrpc": "2.0", "id": payload["id"], "result": []}


def test_get_logs_bisects_oversized_responses() -> None:
    rpc = SplittingRpc()

    assert rpc.get_logs("0x" + "12" * 20, 1, 4) == []
    assert rpc.ranges == [(1, 4), (1, 2), (3, 4)]
