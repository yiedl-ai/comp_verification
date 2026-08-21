from comp_verification.caveats import (
    CAVEATS_DOCUMENT,
    adjudicate_report_mismatches,
    caveat_for_challenge,
)


def test_challenge_eight_references_central_caveat_register() -> None:
    caveat = caveat_for_challenge(8)

    assert caveat is not None
    assert caveat["document"] == CAVEATS_DOCUMENT
    assert caveat["anchor"] == (
        "challenge-8-late-submission-rpc-synchronization-and-ipfs-availability"
    )
    assert caveat_for_challenge(7) is None


def test_accepted_publication_omission_preserves_raw_mismatch() -> None:
    address = "0x61a5c52423560f541ec3c6461318deae0519a4ab"
    report = adjudicate_report_mismatches(
        {
            "passed": False,
            "mismatch_count": 1,
            "mismatches": [
                {
                    "address": address,
                    "field": "participant",
                    "detail": "missing in results",
                }
            ],
        },
        challenge=142,
        competition="UPDOWN",
        audit_kind="publication",
    )

    assert report["raw_passed"] is False
    assert report["passed"] is True
    assert report["passed_with_caveat"] is True
    assert report["raw_mismatch_count"] == 1
    assert report["caveated_mismatch_count"] == 1
    assert report["unresolved_mismatch_count"] == 0
    assert report["mismatches"][0]["caveated_pass"] is True
