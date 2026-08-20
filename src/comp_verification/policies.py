"""Explicit candidate policies, selected by numerical reproduction evidence."""

from dataclasses import dataclass


FIRST_TEN_SYMBOLS = (
    "1INCH",
    "AAVE",
    "ADA",
    "ALGO",
    "ATOM",
    "AVAX",
    "BCH",
    "BTC",
    "CELO",
    "COMP",
    "CRV",
    "DOGE",
    "DOT",
    "ENJ",
    "EOS",
    "ETC",
    "ETH",
    "FIL",
    "ICP",
    "LINK",
    "LTC",
    "MATIC",
    "MKR",
    "NEAR",
    "RUNE",
    "SNX",
    "SOL",
    "SUSHI",
    "TRX",
    "UMA",
    "UNI",
    "XLM",
    "XMR",
    "XTZ",
    "YFI",
    "ZEC",
    "ZRX",
)


@dataclass(frozen=True)
class ScoringPolicy:
    policy_id: str
    symbols: tuple[str, ...]
    prediction_float_roundtrip: bool
    answer_binary_float: bool
    reward_digits: int
    source_git_commit: str
    source_files_sha256: tuple[tuple[str, str], ...]
    status: str


FIRST_TEN_CANDIDATE = ScoringPolicy(
    policy_id="legacy-37-v1",
    symbols=FIRST_TEN_SYMBOLS,
    prediction_float_roundtrip=True,
    answer_binary_float=True,
    reward_digits=6,
    source_git_commit="9f03bb3",
    source_files_sha256=(
        (
            "library/yiedl2.py",
            "6b8ffe243cca0debc341af7c4f76aa05238d396c08d8fa53c000005d6d32807f",
        ),
        (
            "library/score_reward.py",
            "5c302c75b10964ba0203baefe77025dca3099d5ceb77fefa237403d9f30c2363",
        ),
    ),
    status="verified-first-ten-with-reported-operational-mismatch",
)
