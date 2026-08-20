from comp_verification.caveats import CAVEATS_DOCUMENT, caveat_for_challenge


def test_challenge_eight_references_central_caveat_register() -> None:
    caveat = caveat_for_challenge(8)

    assert caveat is not None
    assert caveat["document"] == CAVEATS_DOCUMENT
    assert caveat["anchor"] == "challenge-8-late-submission-and-ipfs-availability"
    assert caveat_for_challenge(7) is None
