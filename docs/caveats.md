# Verification caveats: summary

This page lists only issues needed to interpret the audit result. Every
published reward for challenges 1–177 is reproduced by the verifier. See
[`caveats-details.md`](caveats-details.md) for supporting evidence, resolved
ingestion history, and policy-transition notes.

Raw mismatches remain visible. They count as passes only when explicitly
adjudicated in `problems/register.json`.

## Historical scoring exceptions

| Challenge | Scope | Conclusion |
| --- | --- | --- |
| <a id="challenge-8-late-submission-rpc-synchronization-and-ipfs-availability"></a>8 | Both competitions | The final valid submission was missed in both scoring snapshots; the two zeroed results are accepted historical exceptions. |
| <a id="challenge-19-three-addresses-zeroed-in-both-competitions"></a>19 | Both competitions | The final three valid submitters were omitted from both scoring inputs; the six zeroed results are accepted historical exceptions. |
| <a id="challenge-33-neutral-last-submission-published-as-zero"></a>33 | NEUTRAL | The final valid submission was omitted from the scoring input; its zeroed result is an accepted historical exception. |
| <a id="challenges-40-42-mistake-undo-and-corrected-settlement"></a>40–42 | Both competitions | Challenge 40 was mistaken, challenge 41 reversed it exactly, and challenge 42 posted the correct settlement. The sequence passes as one correction. |
| <a id="challenge-73-neutral-valid-submission-published-as-zero"></a>73 | NEUTRAL | A stricter production validator rejected a submission containing an extra blank-symbol row; the zeroed result is accepted. |
| <a id="challenge-113-hai-target-override-and-stale-updown-result-reference"></a>113 | Both competitions | Production capped hacked asset HAI's settlement return at `1`, bounding its score contribution by allocated margin. The cap reproduces every reward exactly. |

## Corrected result references

The immutable original result references below point to the wrong content. The
correct CIDs are authenticated on-chain under information item 0 for the zero
address and pass both publication and scoring verification.

| Challenge | Scope | Original reference |
| --- | --- | --- |
| <a id="challenge-14-neutral-results-cid-points-to-dataset-15"></a>14 | NEUTRAL | Points to dataset 15. |
| <a id="challenge-28-neutral-results-cid-is-challenge-29-public-key"></a>28 | NEUTRAL | Contains the challenge-29 public key. |
| <a id="challenge-110-stale-updown-result-reference"></a>110 | UPDOWN | Points to challenge 109. |
| 113 | UPDOWN | Points to challenge 112. |
| <a id="challenge-116-stale-updown-result-reference"></a>116 | UPDOWN | Points to challenge 115. |
| <a id="challenge-117-both-result-references-are-one-challenge-late"></a>117 | Both competitions | Both references contain challenge-116 results. |
| <a id="challenge-123-stale-updown-result-reference"></a>123 | UPDOWN | Points to challenge 122. |
| <a id="challenge-134-stale-updown-result-reference"></a>134 | UPDOWN | Points to challenge 133. |

## Remaining evidence limitations

| Challenge | Scope | Limitation |
| --- | --- | --- |
| <a id="challenge-94-updown-malformed-unavailable-submission-reference"></a>94 | UPDOWN | One malformed on-chain submission reference is unavailable; its recorded reward is zero and every available submission verifies. |
| <a id="challenge-95-neutral-malformed-unavailable-submission-reference"></a>95 | NEUTRAL | One malformed on-chain submission reference is unavailable; its recorded reward is zero and every available submission verifies. |
| <a id="challenge-166-unpublished-old-basket-settlement-targets"></a>166 | Both competitions | The exact old-basket settlement dataset was not published. Seven targets were recovered numerically, and every score and reward reproduces exactly. |
