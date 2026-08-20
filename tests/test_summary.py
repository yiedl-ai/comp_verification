import json
from pathlib import Path

from comp_verification.summary import build_audit_status


def _write_report(path: Path, *, passed: bool, audit_status: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"passed": passed, "mismatch_count": 0}
    if audit_status is not None:
        report["audit_status"] = audit_status
    path.write_text(json.dumps(report), encoding="utf-8")


def test_audit_status_distinguishes_passed_failed_and_blocked(tmp_path: Path) -> None:
    for competition in ("neutral", "updown"):
        _write_report(
            tmp_path / "reports" / "publication" / f"challenge-001-{competition}.json",
            passed=True,
        )
        _write_report(
            tmp_path / "reports" / "scoring" / f"challenge-001-{competition}.json",
            passed=True,
        )
    _write_report(
        tmp_path / "reports" / "publication" / "challenge-002-neutral.json",
        passed=False,
    )
    _write_report(
        tmp_path / "reports" / "scoring" / "challenge-002-neutral.json",
        passed=False,
        audit_status="blocked-by-publication-failure",
    )
    target = tmp_path / "data" / "targets" / "challenge-001.csv"
    target.parent.mkdir(parents=True)
    target.write_text("date,symbol,target_updown\n", encoding="utf-8")

    summary = build_audit_status(tmp_path, tmp_path / "reports" / "audit-status.json")

    assert summary["publication_audits"] == {
        "passed": 2,
        "blocked": 0,
        "failed": 1,
        "total": 3,
    }
    assert summary["scoring_audits"] == {
        "passed": 2,
        "blocked": 1,
        "failed": 0,
        "total": 3,
    }
    assert summary["fully_score_audited_challenges"] == [1]
    assert summary["target_ready_challenges"] == [1]
