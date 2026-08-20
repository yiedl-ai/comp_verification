from comp_verification.ingestion import token_amount


def test_token_amount_preserves_contract_units() -> None:
    assert token_amount(0) == {"raw": "0", "decimal": "0.000000"}
    assert token_amount(12_345_678) == {
        "raw": "12345678",
        "decimal": "12.345678",
    }
