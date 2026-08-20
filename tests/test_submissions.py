from decimal import Decimal

import pytest

from comp_verification.submissions import (
    InvalidSubmission,
    parse_dynamic_predictions,
    parse_predictions,
)


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


def test_dynamic_parser_keeps_first_alias_normalized_duplicate_and_partial_rows() -> None:
    parsed = parse_dynamic_predictions(
        b"symbol,prediction,ignored\nRNDR,1,x\nRENDER,9,y\nBTC,2,z\nEXTRA,3,z\n",
        ("BTC", "RENDER", "ETH"),
        aliases={"RNDR": "RENDER"},
    )

    assert parsed.predictions == {"RENDER": Decimal("1"), "BTC": Decimal("2")}
    assert parsed.duplicates == ("RENDER",)
    assert parsed.extras == ("EXTRA",)
    assert parsed.missing == ("ETH",)


def test_dynamic_parser_rejects_nonfinite_values() -> None:
    with pytest.raises(InvalidSubmission, match="non-finite"):
        parse_dynamic_predictions(b"BTC,inf\n", ("BTC",), aliases={})
