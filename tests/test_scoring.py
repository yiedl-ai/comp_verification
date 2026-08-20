from decimal import Decimal
from pathlib import Path

from comp_verification.scoring import (
    explicit_allocation,
    market_neutral_allocation,
    relative_gain,
    score_prediction,
    wallet_reward,
    read_realized_returns,
)


def test_explicit_wallet_score_and_reward() -> None:
    allocation = explicit_allocation(
        {"BTC": Decimal("2"), "ETH": Decimal("-1"), "SOL": Decimal("1")}
    )
    gain = relative_gain(
        allocation,
        {"BTC": Decimal("0.1"), "ETH": Decimal("-0.2"), "SOL": Decimal("0.3")},
    )
    assert allocation == {
        "BTC": Decimal("0.5"),
        "ETH": Decimal("-0.25"),
        "SOL": Decimal("0.25"),
    }
    assert gain == Decimal("0.175")
    assert wallet_reward(Decimal("100"), gain) == Decimal("17.500000")
    assert score_prediction(
        "UPDOWN",
        {"BTC": Decimal("2"), "ETH": Decimal("-1"), "SOL": Decimal("1")},
        {"BTC": Decimal("0.1"), "ETH": Decimal("-0.2"), "SOL": Decimal("0.3")},
        Decimal("100"),
    ) == (Decimal("0.175"), Decimal("17.500000"))


def test_market_neutral_allocation_uses_average_tie_ranks() -> None:
    allocation = market_neutral_allocation(
        {"A": Decimal("5"), "B": Decimal("1"), "C": Decimal("1")}
    )
    assert allocation == {
        "A": Decimal("1") / Decimal("2"),
        "B": Decimal("-1") / Decimal("4"),
        "C": Decimal("-1") / Decimal("4"),
    }


def test_dynamic_answer_uses_decimal_of_pandas_float_string(tmp_path: Path) -> None:
    source = tmp_path / "prices.csv"
    source.write_text("date,symbol,return\n2026-07-12,BTC,0.1\n")

    dynamic = read_realized_returns(
        source, binary_float=False, decimal_from_float_string=True
    )
    legacy = read_realized_returns(source, binary_float=True)

    assert dynamic == {"BTC": Decimal("0.1")}
    assert legacy["BTC"] != Decimal("0.1")
