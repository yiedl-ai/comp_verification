from decimal import Decimal

import pytest

from comp_verification.submissions import InvalidSubmission, parse_predictions


def test_exact_or_absent_header_matches_historical_ingestion() -> None:
    symbols = ("BTC", "ETH")

    assert parse_predictions(b"symbol,prediction\nBTC,1\nETH,-1\n", symbols)
    assert parse_predictions(b"BTC,1\nETH,-1\n", symbols)


def test_wrong_prediction_header_is_rejected() -> None:
    with pytest.raises(InvalidSubmission, match="unexpected prediction header"):
        parse_predictions(
            b"symbol,pred_ud\nBTC,1\nETH,-1\n",
            ("BTC", "ETH"),
        )


def test_historical_pandas_float_parser_is_locked() -> None:
    predictions = parse_predictions(
        b"ADA,-1.9241661184480974\n",
        ("ADA",),
    )

    assert predictions == {"ADA": Decimal("-1.9241661184480972")}
