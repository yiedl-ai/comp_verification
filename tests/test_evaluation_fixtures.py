import zipfile
from pathlib import Path

from comp_verification.datasets import (
    extract_evaluation_universe,
    verify_evaluation_fixture,
    write_evaluation_fixture,
)


def test_evaluation_universe_is_configured_validation_train_intersection(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "dataset.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "dataset/validation_dataset.csv",
            "symbol,feature\nBTC,1\nETH,2\nEXTRA,3\n",
        )
    universe, member = extract_evaluation_universe(
        archive_path,
        dataset_challenge=167,
        source_cid="QmExample",
        configured_symbols=("BTC", "ETH", "SOL"),
        latest_train_symbols={"BTC", "SOL"},
        latest_train_date="2026-06-28",
    )

    assert universe.evaluation_symbols == ("BTC",)
    assert universe.rows == (
        ("BTC", "true", "true", "true"),
        ("ETH", "false", "true", "false"),
        ("SOL", "true", "false", "false"),
    )

    destination = tmp_path / "challenge-167.csv"
    write_evaluation_fixture(universe, member, "a" * 64, destination)
    verify_evaluation_fixture(universe, member, "a" * 64, destination)
