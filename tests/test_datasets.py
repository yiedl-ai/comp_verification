import zipfile
from pathlib import Path

from comp_verification.datasets import extract_latest_realized_returns


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
