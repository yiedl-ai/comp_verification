import hashlib
import json
import zipfile
from pathlib import Path

from comp_verification.datasets import (
    derive_price_fixture_from_targets,
    extract_latest_realized_returns,
    extract_latest_targets,
    verify_target_fixture,
    write_target_fixture,
)


def test_extract_latest_realized_returns(tmp_path: Path) -> None:
    archive_path = tmp_path / "dataset.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "challenge/dataset/train_dataset.csv",
            "date,symbol,feature_1,target_updown,target_neutral\n"
            "2023-05-01,BTC,0.1,0.01,0.75\n"
            "2023-05-01,ETH,0.2,-0.02,0.25\n"
            "2023-05-08,ETH,0.3,0.125,1.0\n"
            "2023-05-08,BTC,0.4,-0.5,0.0\n",
        )

    prices, member = extract_latest_realized_returns(
        archive_path,
        scoring_challenge=1,
        source_dataset_challenge=2,
        source_cid="QmSource",
        symbols=("BTC", "ETH"),
    )

    assert member.filename == "challenge/dataset/train_dataset.csv"
    assert prices.date == "2023-05-08"
    assert prices.rows == (("BTC", "-0.5"), ("ETH", "0.125"))
    assert prices.csv_bytes() == (
        b"date,symbol,return\n"
        b"2023-05-08,BTC,-0.5\n"
        b"2023-05-08,ETH,0.125\n"
    )


def test_extract_latest_targets_preserves_both_targets_and_every_symbol(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "dataset.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "challenge/dataset/train_dataset.csv",
            "date,symbol,target_updown,target_neutral,feature_1\n"
            "2023-05-01,BTC,0.01,0.75,1\n"
            "2023-05-08,ZZZ,0.2,0.3,2\n"
            "2023-05-08,ETH,0.125,1.0,3\n"
            "2023-05-08,BTC,-0.5,0.0,4\n",
        )

    targets, member = extract_latest_targets(
        archive_path,
        scoring_challenge=1,
        source_dataset_challenge=2,
        source_cid="QmSource",
        source_digest="0xsource",
    )

    assert targets.target_columns == ("target_updown", "target_neutral")
    assert targets.rows == (
        ("BTC", "-0.5", "0.0"),
        ("ETH", "0.125", "1.0"),
        ("ZZZ", "0.2", "0.3"),
    )
    destination = tmp_path / "targets.csv"
    write_target_fixture(
        targets,
        member,
        "archive-sha",
        archive_path.stat().st_size,
        "QmSource",
        destination,
    )
    verify_target_fixture(
        targets,
        member,
        "archive-sha",
        archive_path.stat().st_size,
        "QmSource",
        destination,
    )


def test_derive_price_fixture_from_verified_targets(tmp_path: Path) -> None:
    source = tmp_path / "challenge-011.csv"
    source.write_text(
        "date,symbol,target_updown,target_neutral\n"
        "2023-07-23,AAVE,0.1,0.9\n"
        "2023-07-23,BTC,-0.2,0.8\n",
        encoding="utf-8",
    )
    source_bytes = source.read_bytes()
    source.with_suffix(".json").write_text(
        json.dumps(
            {
                "scoring_challenge": 11,
                "source_dataset_challenge": 12,
                "source_cid": "QmSource",
                "source_cid_verified": True,
                "source_archive_sha256": "archive-sha",
                "source_member": "dataset/train_dataset.csv",
                "source_member_crc32": "12345678",
                "source_member_uncompressed_size": 100,
                "date": "2023-07-23",
                "target_columns": ["target_updown", "target_neutral"],
                "targets_sha256": hashlib.sha256(source_bytes).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    destination = tmp_path / "prices.csv"

    provenance = derive_price_fixture_from_targets(
        source,
        symbols=("AAVE", "BTC"),
        policy_id="legacy-37-v1",
        destination=destination,
    )

    assert destination.read_text(encoding="utf-8") == (
        "date,symbol,return\n"
        "2023-07-23,AAVE,0.1\n"
        "2023-07-23,BTC,-0.2\n"
    )
    assert provenance["derived_from_targets_sha256"] == hashlib.sha256(
        source_bytes
    ).hexdigest()
    assert provenance["target_column"] == "target_updown"


def test_derive_price_fixture_records_aliases_and_recovered_overrides(
    tmp_path: Path,
) -> None:
    source = tmp_path / "challenge-166.csv"
    source.write_text(
        "date,symbol,target_updown\n"
        "2026-06-28,DYDX,-0.15\n"
        "2026-06-28,RENDER,0.4\n",
        encoding="utf-8",
    )
    source_bytes = source.read_bytes()
    source.with_suffix(".json").write_text(
        json.dumps(
            {
                "scoring_challenge": 166,
                "source_dataset_challenge": 167,
                "source_cid": "QmSource",
                "source_cid_verified": True,
                "source_archive_sha256": "archive-sha",
                "source_member": "dataset/train_dataset.csv",
                "source_member_crc32": "12345678",
                "source_member_uncompressed_size": 100,
                "date": "2026-06-28",
                "target_columns": ["target_updown"],
                "targets_sha256": hashlib.sha256(source_bytes).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    destination = tmp_path / "prices.csv"

    provenance = derive_price_fixture_from_targets(
        source,
        symbols=("DYDX", "RNDR"),
        policy_id="legacy-static-77-zero-guard",
        destination=destination,
        source_symbol_aliases={"RNDR": "RENDER"},
        realized_return_overrides={"DYDX": "-0.14"},
        override_problem_id="challenge-166-test",
    )

    assert destination.read_text(encoding="utf-8") == (
        "date,symbol,return\n"
        "2026-06-28,DYDX,-0.14\n"
        "2026-06-28,RNDR,0.4\n"
    )
    assert provenance["source_symbol_aliases"] == {"RNDR": "RENDER"}
    assert provenance["realized_return_overrides"] == [
        {
            "symbol": "DYDX",
            "source_value": "-0.15",
            "fixture_value": "-0.14",
            "problem_id": "challenge-166-test",
        }
    ]
