"""Versioned historical scoring policies selected from repository evidence."""

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

CHALLENGE_19_SYMBOLS = tuple(
    symbol for symbol in FIRST_TEN_SYMBOLS if symbol not in {"ALGO", "SOL", "SUSHI"}
)

CHALLENGE_44_SYMBOLS = tuple(
    symbol
    for symbol in FIRST_TEN_SYMBOLS
    if symbol not in {"1INCH", "CELO", "ENJ", "SNX", "UMA", "ZEC", "ZRX"}
)

STATIC_77_SYMBOLS = (
    "AAVE", "ADA", "ALGO", "APE", "APT", "ATOM", "AVAX", "AXS", "BAL", "BCH",
    "BLUR", "BNB", "BONK", "BTC", "C98", "CAKE", "COMP", "CRV", "CVX", "DAI",
    "DAO", "DOGE", "DOT", "DYDX", "EOS", "ETC", "ETH", "FET", "FIL", "FRAX",
    "FTM", "FXS", "GRT", "HAI", "HERO", "ICP", "IMX", "INJ", "LDO", "LINK",
    "LTC", "MATIC", "MAV", "MBOX", "MKR", "MOON", "NEAR", "OP", "PENDLE",
    "PEPE", "PERP", "PIT", "POLS", "PYTH", "QUACK", "RDNT", "RNDR", "RPL",
    "RUNE", "SFP", "SFUND", "SHIB", "SOL", "STG", "SUI", "SUSHI", "TIA",
    "TOKEN", "TRX", "UNI", "USDT", "XLM", "XMR", "XRP", "XTZ", "XVS", "YFI",
)

DYNAMIC_153_SYMBOLS = (
    "BTC", "LTC", "XRP", "DOGE", "DASH", "XMR", "XLM", "ETH", "ETC", "ZEC",
    "ZEN", "IOTA", "BCH", "BNB", "TRX", "LINK", "ADA", "FIL", "SNX", "BSV",
    "FET", "ATOM", "RSR", "ALGO", "RUNE", "LUNC", "HBAR", "PAXG", "STX", "TRB",
    "SOL", "CELO", "UMA", "AR", "RENDER", "COMP", "AVAX", "SHIB", "SAND", "NEAR",
    "CRV", "DOT", "SUSHI", "AXS", "GALA", "UNI", "CAKE", "INJ", "AAVE", "CFX",
    "LDO", "MINA", "ICP", "PENDLE", "IMX", "FLOKI", "TON", "OP", "ARB", "GMX",
    "WLD", "MANTA", "ENS", "PEOPLE", "GMT", "APE", "APEX", "KAS", "SUI", "ONDO",
    "ZETA", "APT", "STRK", "TIA", "TAO", "BONK", "BLUR", "SEI", "ZK", "PEPE",
    "BERA", "TURBO", "ORDI", "ZRO", "MNT", "LINEA", "PYTH", "MEME", "POL", "JTO",
    "WIF", "POPCAT", "NOT", "DYM", "XAI", "ALT", "JUP", "AERO", "VIRTUAL", "W",
    "BRETT", "ETHFI", "IO", "BOME", "sENA", "TNSR", "EIGEN", "MON", "MERL", "REZ",
    "SOPH", "HYPE", "ME", "BABY", "MOVE", "NEIRO", "S", "GRASS", "SKY", "INIT",
    "WCT", "WLFI", "GOAT", "FARTCOIN", "PNUT", "SYRUP", "USUAL", "AIXBT", "MORPHO",
    "PENGU", "GRIFFAIN", "BIO", "ANIME", "TRUMP", "MELANIA", "VINE", "LAYER", "VVV",
    "IP", "NIL", "KAITO", "ZORA", "HYPER", "ASTER", "PUMP", "XPL", "CC", "PROVE",
    "HEMI", "AVNT", "0G", "2Z", "LIT",
)

DYNAMIC_SYMBOL_ALIASES = (
    ("RNDR", "RENDER"),
    ("FTM", "S"),
    ("MATIC", "POL"),
    ("SENA", "sENA"),
    ("sena", "sENA"),
    ("Sena", "sENA"),
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
    score_symbol_order: str = "submission"


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

CHALLENGE_19_CANDIDATE = ScoringPolicy(
    policy_id="legacy-34-challenge-19",
    symbols=CHALLENGE_19_SYMBOLS,
    prediction_float_roundtrip=True,
    answer_binary_float=True,
    reward_digits=6,
    source_git_commit="5a6e3bc",
    source_files_sha256=((
        "library/score_reward.py",
        "4d22a07e7b45edf4a36d4a38a7e36a665f9dbf98d569e7b7697ffa6a6573e938",
    ),),
    status="source-derived-candidate",
)

RESTORED_37_CANDIDATE = ScoringPolicy(
    policy_id="legacy-37-restored",
    symbols=FIRST_TEN_SYMBOLS,
    prediction_float_roundtrip=True,
    answer_binary_float=True,
    reward_digits=6,
    source_git_commit="ad6044c",
    source_files_sha256=((
        "library/score_reward.py",
        "b49e2391d140864ee7555c19d98f03e10c1364ee354b962dea527de0b695eb7b",
    ),),
    status="source-derived-candidate",
)

LEGACY_30_CANDIDATE = ScoringPolicy(
    policy_id="legacy-30-v1",
    symbols=CHALLENGE_44_SYMBOLS,
    prediction_float_roundtrip=True,
    answer_binary_float=True,
    reward_digits=6,
    source_git_commit="c680c8b",
    source_files_sha256=((
        "library/score_reward.py",
        "97250a72922b765b8507a20da94db3ee26e12e8253899cae33430d9c85111f76",
    ),),
    status="source-derived-candidate",
)

STATIC_77_CANDIDATE = ScoringPolicy(
    policy_id="legacy-static-77-v1",
    symbols=STATIC_77_SYMBOLS,
    prediction_float_roundtrip=True,
    answer_binary_float=True,
    reward_digits=6,
    source_git_commit="b783812",
    source_files_sha256=((
        "library/score_reward.py",
        "a4f7e9b783a6366870e9caccb4af9dc277697d81bdf6f7e2797475a3152ecfdb",
    ),),
    status="source-derived-candidate",
)

STATIC_77_ZERO_GUARD_CANDIDATE = ScoringPolicy(
    policy_id="legacy-static-77-zero-guard",
    symbols=STATIC_77_SYMBOLS,
    prediction_float_roundtrip=True,
    answer_binary_float=True,
    reward_digits=6,
    source_git_commit="9d4453b",
    source_files_sha256=((
        "library/score_reward.py",
        "eb77e86b55e4320c2ae7a606f607cf576d0a2d975df66e68581333826a46883d",
    ),),
    status="source-derived-candidate",
)

DYNAMIC_153_CANDIDATE = ScoringPolicy(
    policy_id="dynamic-evaluation-153-v1",
    symbols=DYNAMIC_153_SYMBOLS,
    prediction_float_roundtrip=True,
    answer_binary_float=False,
    reward_digits=6,
    source_git_commit="77e675f",
    source_files_sha256=(
        (
            "library/score_reward.py",
            "7fbf771545ffd3f6d04fa3c6fea1d76f59372365645feb48de296744dee04d42",
        ),
        (
            "library/basket.py",
            "23d3a6ef56de611830dc095b2a4c5f892e56257353bc60c47280e3a6b9c5f19b",
        ),
        (
            "library/yiedl_latest.py",
            "2bd1ece83aa29beaa8fa6e851be9b30ca2688c9e490ba804bff7c655c6e0eb17",
        ),
        (
            "configuration/basket.csv",
            "a4f0fefe9972a4efdea9e2e9d2c3886c3b1486e56a61853e3b1260f8fcec9341",
        ),
        (
            "configuration/basket_aliases.csv",
            "194527937726254f19fb483a89f21195bf7f283ba8a22b30871e865344fcdf18",
        ),
        (
            "archieved/competition.sql",
            "9cd98d96b02ecf9d8db467588fe08aab29090cd1cf2934c9b36ec0eed1000b72",
        ),
    ),
    status="source-derived-candidate",
    # PostgreSQL's historical submission_series_address_symbol index supplied
    # the rows in symbol order to the production SELECT used by the scorer.
    score_symbol_order="symbol",
)


def policy_for_challenge(challenge: int) -> ScoringPolicy:
    """Return the source-backed static policy candidate for a challenge."""

    if 1 <= challenge <= 18:
        return FIRST_TEN_CANDIDATE
    if challenge == 19:
        return CHALLENGE_19_CANDIDATE
    if 20 <= challenge <= 40:
        return RESTORED_37_CANDIDATE
    if 41 <= challenge <= 51:
        return LEGACY_30_CANDIDATE
    if 52 <= challenge <= 163:
        return STATIC_77_CANDIDATE
    if 164 <= challenge <= 166:
        return STATIC_77_ZERO_GUARD_CANDIDATE
    if 167 <= challenge <= 179:
        return DYNAMIC_153_CANDIDATE
    raise ValueError(f"challenge {challenge} does not use a static scoring policy")
