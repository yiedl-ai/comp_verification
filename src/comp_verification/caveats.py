"""References into the verifier's central caveat register."""

from __future__ import annotations

from typing import Any


CAVEATS_DOCUMENT = "docs/caveats.md"


def caveat_for_challenge(challenge: int) -> dict[str, Any] | None:
    """Return a report-safe caveat reference for a historical challenge."""

    if challenge == 8:
        return {
            "id": "challenge-8-late-submission-rpc-sync-and-ipfs-availability",
            "document": CAVEATS_DOCUMENT,
            "anchor": (
                "challenge-8-late-submission-rpc-synchronization-and-ipfs-availability"
            ),
            "classification": "inferred-operational-exception",
            "summary": (
                "The early backend likely captured submissions before the final "
                "on-chain close state, read from a lagging RPC, or encountered "
                "late IPFS availability; the affected comparisons remain scoring "
                "failures."
            ),
        }
    return None
