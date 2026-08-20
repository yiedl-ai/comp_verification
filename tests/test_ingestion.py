from pathlib import Path

from comp_verification.constants import CONTRACTS, REGISTRY_ADDRESS
from comp_verification.ingestion import ingest_dataset_catalog, token_amount


def test_token_amount_preserves_contract_units() -> None:
    assert token_amount(0) == {"raw": "0", "decimal": "0.000000"}
    assert token_amount(12_345_678) == {
        "raw": "12345678",
        "decimal": "12.345678",
    }


class _DatasetRpc:
    def __init__(self) -> None:
        self.calls = []

    def block_number(self) -> int:
        return 456

    def multicall(self, calls, registry, *, block="latest"):
        self.calls = list(calls)
        self.registry = registry
        self.block = block
        return [
            "0x" + f"{challenge:064x}"
            for challenge in (1, 1, 173, 173)
        ]


def test_dataset_catalog_batches_both_contracts_at_one_block(tmp_path: Path) -> None:
    rpc = _DatasetRpc()

    catalog = ingest_dataset_catalog(rpc, [1, 173], tmp_path / "datasets.json")

    assert len(rpc.calls) == 2 * len(CONTRACTS)
    assert rpc.registry == REGISTRY_ADDRESS
    assert rpc.block == hex(456)
    assert [row["challenge"] for row in catalog["datasets"]] == [1, 173]
    assert catalog["datasets"][1]["contract_digests"]["UPDOWN"] == (
        "0x" + f"{173:064x}"
    )
