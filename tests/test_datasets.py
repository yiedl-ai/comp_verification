import zipfile
from pathlib import Path

from comp_verification.datasets import (
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
