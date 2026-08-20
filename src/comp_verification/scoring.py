"""Pure Decimal candidate implementations of the historical wallet scorer."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Mapping

import pandas as pd


def read_realized_returns(
    path: Path, *, binary_float: bool, decimal_from_float_string: bool = False
) -> dict[str, Decimal]:
    if binary_float and decimal_from_float_string:
        raise ValueError("realized-return conversion modes are mutually exclusive")
    if binary_float:
        frame = pd.read_csv(path)
        return {
            str(row.symbol): Decimal(float(row["return"]))
            for _, row in frame.iterrows()
        }
    if decimal_from_float_string:
        frame = pd.read_csv(path)
        return {
            str(row.symbol): Decimal(str(row["return"]))
            for _, row in frame.iterrows()
        }
    frame = pd.read_csv(path, dtype=str)
    return {
        str(row.symbol): Decimal(str(row["return"]))
        for _, row in frame.iterrows()
    }


def explicit_allocation(prediction: Mapping[str, Decimal]) -> dict[str, Decimal]:
    margin = sum((abs(value) for value in prediction.values()), Decimal(0))
    if margin == 0:
        raise ValueError("zero-margin prediction")
    return {symbol: value / margin for symbol, value in prediction.items()}


def market_neutral_allocation(
    prediction: Mapping[str, Decimal],
) -> dict[str, Decimal]:
    symbols = list(prediction)
    ranks = _average_ranks([prediction[symbol] for symbol in symbols])
    denominator = Decimal(len(ranks) - 1)
    centered = {
        symbol: Decimal(2) * (rank - Decimal(1)) / denominator - Decimal(1)
        for symbol, rank in zip(symbols, ranks, strict=True)
    }
    return explicit_allocation(centered)


def relative_gain(
    allocation: Mapping[str, Decimal], realized_returns: Mapping[str, Decimal]
) -> Decimal:
    return sum(
        (quantity * realized_returns[symbol] for symbol, quantity in allocation.items()),
        Decimal(0),
    )


def wallet_reward(stake: Decimal, gain: Decimal, digits: int = 6) -> Decimal:
    return round(stake * gain, digits)


def score_prediction(
    competition: str,
    prediction: Mapping[str, Decimal],
    realized_returns: Mapping[str, Decimal],
    stake: Decimal,
    *,
    reward_digits: int = 6,
) -> tuple[Decimal, Decimal]:
    if competition == "UPDOWN":
        allocation = explicit_allocation(prediction)
    elif competition == "NEUTRAL":
        allocation = market_neutral_allocation(prediction)
    else:
        raise ValueError(f"unknown competition {competition}")
    gain = relative_gain(allocation, realized_returns)
    return gain, wallet_reward(stake, gain, reward_digits)


def _average_ranks(values: list[Decimal]) -> list[Decimal]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [Decimal(0)] * len(values)
    start = 0
    while start < len(indexed):
        end = start + 1
        while end < len(indexed) and indexed[end][1] == indexed[start][1]:
            end += 1
        average = (Decimal(start + 1) + Decimal(end)) / Decimal(2)
        for position in range(start, end):
            ranks[indexed[position][0]] = average
        start = end
    return ranks
