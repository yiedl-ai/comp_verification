"""Typed access to the persistent verification problem register."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REGISTER_SCHEMA_VERSION = 1
DEFAULT_REGISTER_PATH = (
    Path(__file__).resolve().parents[2] / "problems" / "register.json"
)


class ProblemRegisterError(ValueError):
    """Raised when the problem register is malformed or internally inconsistent."""


@dataclass(frozen=True)
class ProblemScope:
    """The audit contexts to which a registered problem applies."""

    challenges: frozenset[int]
    competitions: frozenset[str]
    audit_kinds: frozenset[str]
    addresses: frozenset[str]

    def matches(
        self,
        *,
        challenge: int,
        competition: str | None = None,
        audit_kind: str | None = None,
        address: str | None = None,
    ) -> bool:
        """Return whether a supplied audit context intersects this scope.

        Omitted optional fields are wildcards. This lets a challenge-level report
        discover an address-specific problem while a participant-level report can
        narrow the match precisely.
        """

        if challenge not in self.challenges:
            return False
        if competition is not None and self.competitions:
            if competition.upper() not in self.competitions:
                return False
        if audit_kind is not None and self.audit_kinds:
            if audit_kind.lower() not in self.audit_kinds:
                return False
        if address is not None and self.addresses:
            if address.lower() not in self.addresses:
                return False
        return True


@dataclass(frozen=True)
class RegisteredProblem:
    """One evidence-backed problem, including its report annotation policy."""

    id: str
    headline: str
    status: str
    classification: str
    confidence: str
    scope: ProblemScope
    audit_treatment: Mapping[str, Any]
    documentation: Mapping[str, str]
    raw: Mapping[str, Any]

    @property
    def counts_as_pass(self) -> bool:
        """Whether a matching raw mismatch is an accepted caveated pass."""

        return (
            self.status == "accepted"
            and self.audit_treatment["changes_outcome"] is True
        )

    def matches(
        self,
        *,
        challenge: int,
        competition: str | None = None,
        audit_kind: str | None = None,
        address: str | None = None,
    ) -> bool:
        return self.scope.matches(
            challenge=challenge,
            competition=competition,
            audit_kind=audit_kind,
            address=address,
        )

    def report_reference(self) -> dict[str, Any]:
        """Return the compact reference and explicit adjudication for reports."""

        return {
            "id": self.id,
            "document": self.documentation["document"],
            "anchor": self.documentation["anchor"],
            "classification": self.classification,
            "summary": self.documentation["summary"],
            "counts_as_pass": self.counts_as_pass,
        }


@dataclass(frozen=True)
class ProblemRegister:
    """Validated collection of historical verification problems."""

    schema_version: int
    problems: tuple[RegisteredProblem, ...]

    def find(
        self,
        *,
        challenge: int,
        competition: str | None = None,
        audit_kind: str | None = None,
        address: str | None = None,
    ) -> tuple[RegisteredProblem, ...]:
        return tuple(
            problem
            for problem in self.problems
            if problem.matches(
                challenge=challenge,
                competition=competition,
                audit_kind=audit_kind,
                address=address,
            )
        )

    def by_id(self, problem_id: str) -> RegisteredProblem:
        for problem in self.problems:
            if problem.id == problem_id:
                return problem
        raise KeyError(problem_id)


def load_problem_register(path: Path = DEFAULT_REGISTER_PATH) -> ProblemRegister:
    """Load and validate the canonical JSON register."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProblemRegisterError(f"cannot read problem register {path}: {error}") from error

    if not isinstance(payload, dict):
        raise ProblemRegisterError("problem register root must be an object")
    if payload.get("schema_version") != REGISTER_SCHEMA_VERSION:
        raise ProblemRegisterError(
            f"unsupported problem register schema: {payload.get('schema_version')!r}"
        )
    rows = payload.get("problems")
    if not isinstance(rows, list):
        raise ProblemRegisterError("problem register 'problems' must be an array")

    problems = tuple(_parse_problem(row, index) for index, row in enumerate(rows))
    identifiers = [problem.id for problem in problems]
    if len(identifiers) != len(set(identifiers)):
        raise ProblemRegisterError("problem ids must be unique")
    return ProblemRegister(schema_version=REGISTER_SCHEMA_VERSION, problems=problems)


def _parse_problem(value: object, index: int) -> RegisteredProblem:
    location = f"problems[{index}]"
    if not isinstance(value, dict):
        raise ProblemRegisterError(f"{location} must be an object")

    status = _nonempty_string(value.get("status"), f"{location}.status")

    scope_value = value.get("scope")
    if not isinstance(scope_value, dict):
        raise ProblemRegisterError(f"{location}.scope must be an object")
    challenges = scope_value.get("challenges")
    if (
        not isinstance(challenges, list)
        or not challenges
        or any(type(challenge) is not int or challenge < 1 for challenge in challenges)
    ):
        raise ProblemRegisterError(
            f"{location}.scope.challenges must contain positive integers"
        )
    if len(challenges) != len(set(challenges)):
        raise ProblemRegisterError(f"{location}.scope.challenges must be unique")

    treatment = value.get("audit_treatment")
    if not isinstance(treatment, dict):
        raise ProblemRegisterError(f"{location}.audit_treatment must be an object")
    if not isinstance(treatment.get("changes_outcome"), bool):
        raise ProblemRegisterError(
            f"{location}.audit_treatment.changes_outcome must be a boolean"
        )
    if (status == "accepted") != treatment["changes_outcome"]:
        raise ProblemRegisterError(
            f"{location} accepted status and changes_outcome must agree"
        )

    documentation = value.get("documentation")
    if not isinstance(documentation, dict):
        raise ProblemRegisterError(f"{location}.documentation must be an object")
    parsed_documentation = {
        key: _nonempty_string(documentation.get(key), f"{location}.documentation.{key}")
        for key in ("document", "anchor", "summary")
    }

    return RegisteredProblem(
        id=_nonempty_string(value.get("id"), f"{location}.id"),
        headline=_nonempty_string(value.get("headline"), f"{location}.headline"),
        status=status,
        classification=_nonempty_string(
            value.get("classification"), f"{location}.classification"
        ),
        confidence=_nonempty_string(value.get("confidence"), f"{location}.confidence"),
        scope=ProblemScope(
            challenges=frozenset(challenges),
            competitions=frozenset(
                item.upper()
                for item in _string_list(
                    scope_value.get("competitions"),
                    f"{location}.scope.competitions",
                )
            ),
            audit_kinds=frozenset(
                item.lower()
                for item in _string_list(
                    scope_value.get("audit_kinds"),
                    f"{location}.scope.audit_kinds",
                )
            ),
            addresses=frozenset(
                item.lower()
                for item in _string_list(
                    scope_value.get("addresses"),
                    f"{location}.scope.addresses",
                )
            ),
        ),
        audit_treatment=treatment,
        documentation=parsed_documentation,
        raw=value,
    )


def _nonempty_string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProblemRegisterError(f"{location} must be a non-empty string")
    return value


def _string_list(value: object, location: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ProblemRegisterError(f"{location} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ProblemRegisterError(f"{location} must contain unique values")
    return value
