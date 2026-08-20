"""Report-safe references into the persistent problem register."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .problem_register import ProblemRegister, load_problem_register


CAVEATS_DOCUMENT = "docs/caveats.md"


@lru_cache(maxsize=1)
def _register() -> ProblemRegister:
    return load_problem_register()


def caveats_for_context(
    *,
    challenge: int,
    competition: str | None = None,
    audit_kind: str | None = None,
    address: str | None = None,
) -> list[dict[str, Any]]:
    """Return every registered caveat that intersects an audit context."""

    return [
        problem.report_reference()
        for problem in _register().find(
            challenge=challenge,
            competition=competition,
            audit_kind=audit_kind,
            address=address,
        )
    ]


def caveat_for_challenge(challenge: int) -> dict[str, Any] | None:
    """Return the first challenge caveat for backward-compatible reports."""

    matches = caveats_for_context(challenge=challenge, audit_kind="scoring")
    return matches[0] if matches else None
