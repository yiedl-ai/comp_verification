"""Build compact, machine-readable summaries from detailed audit evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .jsonio import write_canonical_json


def build_first_ten_summary(root: Path, destination: Path) -> dict[str, Any]:
    chain_report = _read(root / "reports" / "chain" / "snapshot-verification.json")
    event_report = _read(root / "reports" / "chain" / "event-verification.json")
    price_report = _read(root / "reports" / "prices" / "verification.json")
    challenges = []
    publication_passes = 0
    scoring_passes = 0
    issue_count = 0
    for challenge in range(1, 11):
        manifest = _read(root / "manifests" / "chain" / f"challenge-{challenge:03d}.json")
        event_path = root / "manifests" / "chain-events" / f"challenge-{challenge:03d}.json"
        event_manifest = _read(event_path) if event_path.exists() else None
        competitions = []
        for competition in ("NEUTRAL", "UPDOWN"):
            suffix = f"challenge-{challenge:03d}-{competition.lower()}.json"
            publication = _read(root / "reports" / "publication" / suffix)
            scoring = _read(root / "reports" / "scoring" / suffix)
            submissions = _read(root / "reports" / "submissions" / suffix)
            issues = []
            for participant in scoring["participants"]:
                if (
                    participant["relative_gain_matches"]
                    and participant["wallet_reward_matches"]
                ):
                    continue
                issue = {
                    "address": participant["address"],
                    "submission_status": participant["submission_status"],
                    "computed_relative_gain": participant["computed_relative_gain"],
                    "published_relative_gain": participant["published_relative_gain"],
                    "computed_wallet_reward": participant["computed_wallet_reward"],
                    "published_wallet_reward": participant["published_wallet_reward"],
                    "classification": "score-or-reward-mismatch",
                }
                event = _submission_event(
                    event_manifest,
                    competition,
                    participant["address"],
                )
                if event is not None:
                    close_block = manifest["competitions"][competition][
                        "submission_closed_block"
                    ]
                    issue["submission_event"] = {
                        "block_number": event["block_number"],
                        "blocks_before_close": close_block - event["block_number"],
                        "block_hash": event["block_hash"],
                        "transaction_hash": event["transaction_hash"],
                        "submission_digest": event["topics"][3],
                    }
                if caveat := scoring.get("caveat"):
                    issue["caveat"] = caveat
                issues.append(issue)
            publication_passes += int(publication["passed"])
            scoring_passes += int(scoring["passed"])
            issue_count += len(issues)
            competitions.append(
                {
                    "competition": competition,
                    "publication_passed": publication["passed"],
                    "scoring_passed": scoring["passed"],
                    "participant_count": scoring["participant_count"],
                    "valid_submission_count": submissions["valid_submission_count"],
                    "maximum_absolute_gain_delta": scoring[
                        "maximum_absolute_gain_delta"
                    ],
                    "issues": issues,
                }
            )
        challenges.append(
            {
                "challenge": challenge,
                "passed": all(
                    item["publication_passed"] and item["scoring_passed"]
                    for item in competitions
                ),
                "competitions": competitions,
            }
        )
    summary = {
        "schema_version": 1,
        "challenge_range": [1, 10],
        "status": "passed" if issue_count == 0 else "issues-found",
        "chain_snapshots_passed": chain_report["passed"],
        "chain_events_passed": event_report["passed"],
        "price_fixtures_passed": price_report["passed"],
        "publication_audits": {"passed": publication_passes, "total": 20},
        "scoring_audits": {"passed": scoring_passes, "total": 20},
        "issue_count": issue_count,
        "challenges": challenges,
    }
    write_canonical_json(destination, summary)
    destination.with_suffix(".md").write_text(
        _render_markdown(summary),
        encoding="utf-8",
    )
    return summary


def _submission_event(
    event_manifest: dict[str, Any] | None,
    competition: str,
    address: str,
) -> dict[str, Any] | None:
    if event_manifest is None:
        return None
    encoded_address = address.removeprefix("0x").lower()
    matches = [
        event
        for event in event_manifest["competitions"][competition]["events"]
        if event["event"] == "SubmissionUpdated"
        and len(event["topics"]) >= 4
        and event["topics"][2].endswith(encoded_address)
    ]
    return matches[-1] if matches else None


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# First-ten verification summary",
        "",
        f"- Chain snapshots: {'PASS' if summary['chain_snapshots_passed'] else 'FAIL'}",
        f"- Chain events: {'PASS' if summary['chain_events_passed'] else 'FAIL'}",
        f"- Price fixtures: {'PASS' if summary['price_fixtures_passed'] else 'FAIL'}",
        (
            "- Publication audits: "
            f"{summary['publication_audits']['passed']}/{summary['publication_audits']['total']} PASS"
        ),
        (
            "- Independent scoring audits: "
            f"{summary['scoring_audits']['passed']}/{summary['scoring_audits']['total']} PASS"
        ),
        f"- Unresolved score/reward mismatches: {summary['issue_count']}",
        "",
        "## Unresolved findings",
        "",
    ]
    for challenge in summary["challenges"]:
        for competition in challenge["competitions"]:
            for issue in competition["issues"]:
                lines.extend(
                    [
                        f"### Challenge {challenge['challenge']} {competition['competition']}",
                        "",
                        f"- Address: `{issue['address']}`",
                        f"- Submission status: `{issue['submission_status']}`",
                        (
                            "- Relative gain: computed "
                            f"`{issue['computed_relative_gain']}`, published "
                            f"`{issue['published_relative_gain']}`"
                        ),
                        (
                            "- Wallet reward/burn: computed "
                            f"`{issue['computed_wallet_reward']}`, published "
                            f"`{issue['published_wallet_reward']}`"
                        ),
                    ]
                )
                event = issue.get("submission_event")
                if event:
                    lines.extend(
                        [
                            (
                                "- Submission event: block "
                                f"`{event['block_number']}` "
                                f"({event['blocks_before_close']} blocks before close)"
                            ),
                            f"- Transaction: `{event['transaction_hash']}`",
                            f"- Block hash: `{event['block_hash']}`",
                        ]
                    )
                caveat = issue.get("caveat")
                if caveat:
                    lines.append(
                        "- Caveat: "
                        f"[{caveat['id']}](../../{caveat['document']}#{caveat['anchor']})"
                    )
                lines.extend(
                    [
                        "",
                        (
                            "The recovered production policy accepts this decrypted submission. "
                            "The published zero remains an audit failure unless separate evidence "
                            "justifies its exclusion."
                        ),
                        "",
                    ]
                )
    if summary["issue_count"] == 0:
        lines.extend(["No unresolved mismatches.", ""])
    return "\n".join(lines)
