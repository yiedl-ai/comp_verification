import pytest

from comp_verification.policies import (
    DYNAMIC_153_SYMBOLS,
    DYNAMIC_SYMBOL_ALIASES,
    policy_for_challenge,
)


@pytest.mark.parametrize(
    ("challenge", "policy_id", "symbol_count"),
    [
        (1, "legacy-37-v1", 37),
        (18, "legacy-37-v1", 37),
        (19, "legacy-34-challenge-19", 34),
        (20, "legacy-37-restored", 37),
        (43, "legacy-37-restored", 37),
        (44, "legacy-30-v1", 30),
        (52, "legacy-30-v1", 30),
        (53, "legacy-static-77-v1", 77),
        (163, "legacy-static-77-v1", 77),
        (164, "legacy-static-77-zero-guard", 77),
        (166, "legacy-static-77-zero-guard", 77),
        (167, "dynamic-evaluation-153-v1", 153),
        (172, "dynamic-evaluation-153-v1", 153),
    ],
)
def test_policy_boundaries(challenge: int, policy_id: str, symbol_count: int) -> None:
    policy = policy_for_challenge(challenge)
    assert policy.policy_id == policy_id
    assert len(policy.symbols) == symbol_count


@pytest.mark.parametrize("challenge", [0, 173])
def test_dynamic_or_out_of_range_challenges_are_not_static(challenge: int) -> None:
    with pytest.raises(ValueError):
        policy_for_challenge(challenge)


def test_dynamic_basket_and_aliases_match_the_source_configuration() -> None:
    assert len(DYNAMIC_153_SYMBOLS) == 153
    assert len(set(DYNAMIC_153_SYMBOLS)) == 153
    assert dict(DYNAMIC_SYMBOL_ALIASES) == {
        "RNDR": "RENDER",
        "FTM": "S",
        "MATIC": "POL",
        "SENA": "sENA",
        "sena": "sENA",
        "Sena": "sENA",
    }
