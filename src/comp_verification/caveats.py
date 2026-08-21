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


def adjudicate_report_mismatches(
    report: dict[str, Any],
    *,
    challenge: int,
    competition: str,
    audit_kind: str,
) -> dict[str, Any]:
    """Apply address-scoped accepted caveats while preserving raw mismatches."""

    if report.get("passed") or not isinstance(report.get("mismatches"), list):
        return report
    annotated = []
    for mismatch in report["mismatches"]:
        caveats = caveats_for_context(
            challenge=challenge,
            competition=competition,
            audit_kind=audit_kind,
            address=mismatch.get("address"),
        )
        caveated_pass = any(item["counts_as_pass"] for item in caveats)
        annotated.append(
            {
                **mismatch,
                "caveated_pass": caveated_pass,
                "effective_match": caveated_pass,
                "caveats": caveats,
            }
        )
    unresolved = [item for item in annotated if not item["caveated_pass"]]
    caveated = [item for item in annotated if item["caveated_pass"]]
    return {
        **report,
        "raw_passed": False,
        "raw_mismatch_count": len(annotated),
        "caveated_mismatch_count": len(caveated),
        "unresolved_mismatch_count": len(unresolved),
        "passed": not unresolved,
        "passed_with_caveat": bool(caveated) and not unresolved,
        "caveats": caveats_for_context(
            challenge=challenge,
            competition=competition,
            audit_kind=audit_kind,
        ),
        "mismatches": annotated,
    }
