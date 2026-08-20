import json
import hashlib
import zipfile
from pathlib import Path

import pytest

from comp_verification.config import (
    IpfsConfig,
    RpcConfig,
    ScopeConfig,
    VerifierConfig,
)
from comp_verification.evidence_workflow import EvidenceWorkflow
from comp_verification.encoding import file_cid_v0
from comp_verification.ipfs import IpfsGateway
from comp_verification.workflow import FirstTenWorkflow


_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _workflow(root: Path) -> EvidenceWorkflow:
    return EvidenceWorkflow(
        root,
        VerifierConfig(
            rpc=RpcConfig("https://polygon.example"),
            ipfs=IpfsConfig("https://ipfs.example/ipfs"),
            scope=ScopeConfig(
                first_challenge=1,
                last_challenge=173,
                last_dataset_challenge=173,
            ),
        ),
    )


def test_dataset_168_gap_writes_explicit_blocked_scoring_reports(
    tmp_path: Path,
) -> None:
    workflow = FirstTenWorkflow(tmp_path, _workflow(tmp_path).config)
    directory = tmp_path / "manifests" / "chain"
    directory.mkdir(parents=True)
    (directory / "challenge-167.json").write_text(
        json.dumps(
            {
                "challenge": 167,
                "competitions": {
                    competition: {
                        "content": {"results": {"cid": f"cid-{competition.lower()}"}},
                        "participants": [],
                    }
                    for competition in ("NEUTRAL", "UPDOWN")
                },
            }
        ),
        encoding="utf-8",
    )

    reports = workflow.audit_scoring(challenges=range(167, 168))

    assert len(reports) == 2
    assert all(row["audit_status"] == "blocked-by-dataset-ingestion" for row in reports)
    assert all(row["passed"] is False for row in reports)
    assert all(row["caveats"][0]["id"].startswith("dataset-168-") for row in reports)


def test_scope_selection_is_bounded_and_deduplicated(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)

    assert workflow._select_challenges([11, 12], range(1, 174), "challenge") == [
        11,
        12,
    ]
    with pytest.raises(ValueError, match="exceeds configured scope"):
        workflow._select_challenges([174], range(1, 174), "challenge")
    with pytest.raises(ValueError, match="duplicates"):
        workflow._select_challenges([11, 11], range(1, 174), "challenge")


def test_chain_manifest_selection_requires_every_requested_file(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    directory = tmp_path / "manifests" / "chain"
    directory.mkdir(parents=True)
    (directory / "challenge-011.json").write_text(
        json.dumps({"challenge": 11}), encoding="utf-8"
    )

    assert workflow._chain_manifests([11]) == [{"challenge": 11}]
    with pytest.raises(ValueError, match=r"missing challenges: \[12\]"):
        workflow._chain_manifests([11, 12])


def test_dataset_download_uses_only_requested_catalog_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _workflow(tmp_path)
    directory = tmp_path / "manifests"
    directory.mkdir()
    (directory / "datasets.json").write_text(
        json.dumps(
            {
                "datasets": [
                    {"challenge": 11, "dataset": {"cid": "cid-11"}},
                    {"challenge": 12, "dataset": {"cid": "cid-12"}},
                ]
            }
        ),
        encoding="utf-8",
    )

    class _Ipfs:
        def download_many(self, cids, *, progress=None):
            self.cids = list(cids)
            return self.cids

    ipfs = _Ipfs()
    monkeypatch.setattr(EvidenceWorkflow, "ipfs", property(lambda self: ipfs))

    assert workflow.download_datasets(challenges=[12]) == ["cid-12"]
    assert ipfs.cids == ["cid-12"]


def _cid_digest(cid: str) -> str:
    number = 0
    for character in cid:
        number = number * 58 + _BASE58.index(character)
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    raw = b"\0" * (len(cid) - len(cid.lstrip("1"))) + raw
    assert raw[:2] == b"\x12\x20"
    return "0x" + raw[2:].hex()


def _cache_dataset(root: Path, label: str) -> tuple[str, Path]:
    temporary = root / f"{label}.zip"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "challenge/dataset/train_dataset.csv",
            "date,symbol,target_updown,target_neutral\n"
            f"2023-05-01,OLD,0.1,0.2\n"
            f"2023-05-08,BTC,{label}.1,{label}.2\n"
            f"2023-05-08,NEW,{label}.3,{label}.4\n",
        )
    cid = file_cid_v0(temporary)
    cache = root / ".cache" / "ipfs"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / cid
    temporary.replace(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (cache / f"{cid}.complete").write_text(
        json.dumps(
            {"sha256": digest, "size": path.stat().st_size},
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="ascii",
    )
    return cid, path


def test_condensation_is_sequential_lossless_verified_and_prunable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _workflow(tmp_path)
    cid_2, raw_2 = _cache_dataset(tmp_path, "2")
    cid_3, raw_3 = _cache_dataset(tmp_path, "3")
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "datasets.json").write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "challenge": 2,
                        "dataset": {"cid": cid_2, "digest": _cid_digest(cid_2)},
                    },
                    {
                        "challenge": 3,
                        "dataset": {"cid": cid_3, "digest": _cid_digest(cid_3)},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    class _OrderedGateway(IpfsGateway):
        def download(self, cid, **kwargs):
            self.order.append(cid)
            return super().download(cid, **kwargs)

    gateway = _OrderedGateway("https://ipfs.example/ipfs", tmp_path / ".cache" / "ipfs")
    gateway.order = []
    monkeypatch.setattr(EvidenceWorkflow, "ipfs", property(lambda self: gateway))

    completed = workflow.condense_score_ready_datasets(
        scoring_challenges=[1, 2], prune_raw=True
    )

    assert gateway.order == [cid_2, cid_3]
    assert [row["symbol_count"] for row in completed] == [2, 2]
    assert all(row["target_columns"] == ["target_updown", "target_neutral"] for row in completed)
    assert not raw_2.exists() and not raw_3.exists()
    fixture = (tmp_path / "data" / "targets" / "challenge-001.csv").read_text()
    assert "2023-05-08,BTC,2.1,2.2" in fixture
    assert "2023-05-08,NEW,2.3,2.4" in fixture
    provenance = json.loads(
        (tmp_path / "data" / "targets" / "challenge-001.json").read_text()
    )
    assert provenance["source_cid_verified"] is True
    assert provenance["row_count"] == 2


def test_failed_fixture_reverification_never_prunes_raw_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _workflow(tmp_path)
    cid, raw = _cache_dataset(tmp_path, "2")
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "datasets.json").write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "challenge": 2,
                        "dataset": {"cid": cid, "digest": _cid_digest(cid)},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    gateway = IpfsGateway("https://ipfs.example/ipfs", tmp_path / ".cache" / "ipfs")
    monkeypatch.setattr(EvidenceWorkflow, "ipfs", property(lambda self: gateway))
    monkeypatch.setattr(
        "comp_verification.evidence_workflow.verify_target_fixture",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("fixture mismatch")),
    )

    with pytest.raises(ValueError, match="fixture mismatch"):
        workflow.condense_score_ready_datasets(
            scoring_challenges=[1], prune_raw=True
        )

    assert raw.exists()
    assert raw.with_name(f"{cid}.complete").exists()
