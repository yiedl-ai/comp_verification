# Verification caveats

This is the central register of limitations, historical exceptions, and
operational explanations used by the competition verifier. Generated reports
reference entries in this document. Raw comparisons are always retained. A
caveat changes the reported outcome only when its machine-readable problem entry
contains an explicit accepted adjudication.

## General caveats

- Historical scoring code may have included production-only changes that were
  never committed. A recovered policy is accepted only after numerical
  reproduction against published results, and its source commit and file hashes
  are recorded in each scoring report.
- Parser and numeric behavior are part of the historical policy. The first-ten
  verifier pins Python, pandas, and NumPy and requires exact score and
  six-decimal reward reproduction with zero tolerance.
- A CID recorded on-chain identifies content but does not, by itself, guarantee
  that the content remained available from an IPFS peer or gateway at every
  historical moment.
- Matching a published result file to Polygon proves publication integrity; it
  does not prove that the off-chain calculation was correct. Scoring audits are
  reported separately.

## Challenge caveat register

| Challenge | Scope | Classification | Affected submissions | Audit treatment |
| --- | --- | --- | ---: | --- |
| 8 | NEUTRAL and UPDOWN | Likely submission-snapshot/RPC-sync/IPFS-availability race | 2 | Accepted as two caveated passes; raw mismatches remain visible |
| 14 | NEUTRAL publication | Results CID is the challenge 15 dataset CID | 1 | Unresolved publication failure; does not count as a pass |

## Challenge 14 NEUTRAL: results CID points to dataset 15

At observed Polygon block `92336519`, challenge 14 NEUTRAL records results CID
`QmNXo5RtUahWHGB578jmkSNK3GSyRxmjRkYUYqoCDosCVd` and digest
`0x02dad9a83f016fd3b4763359ed358478768387df48665531a68f993130f4a0f8`.
Those are exactly the CID and digest recorded for the challenge 15 dataset.

The bytes were independently downloaded and CID-verified. Their SHA-256 is
`1e1adbc58045f0032091792c01e77a26d015d614cd251750750231c3c705f6a7`.
They form a ZIP archive containing `dataset/train_dataset.csv`,
`dataset/validation_dataset.csv`, and a quickstart notebook—not a published
results CSV. Therefore challenge 14 NEUTRAL publication integrity, posted
relative gains, and the complete off-chain score calculation cannot currently
be verified from that on-chain content reference. This remains unresolved and
does not count as a pass.

## Challenge 8: late submission, RPC synchronization, and IPFS availability

### Observed facts

| Competition | Address | Submission CID | Submitted (UTC) | Closed (UTC) | Before close | Computed reward/burn | Published |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| NEUTRAL | `0x8a8e1c4e454e092fc19c6cca2034bd22b29781e7` | `QmckC49ng6oBt3Bbsg8Q2HYefBq41ri1H3x3pXjUzLuVcm` | 2023-07-04 00:37:49 | 2023-07-04 00:49:05 | 11m 16s | `-2.890565` | `0` |
| UPDOWN | `0x8a8e1c4e454e092fc19c6cca2034bd22b29781e7` | `QmWDDvp3H38SgKPX7RNfhDQy16VT9tpqjqaFafpeAYhQCX` | 2023-07-04 00:43:49 | 2023-07-04 00:48:29 | 4m 40s | `-4.412622` | `0` |

The transaction times above are the timestamps of the canonical Polygon blocks
returned by RPC. The independently observed IPFS upload times are approximate
and use Singapore time (UTC+8):

| Competition | Approximate IPFS upload (SGT) | Polygon block inclusion (SGT) | Upload to inclusion | Block | Transaction |
| --- | --- | --- | ---: | ---: | --- |
| NEUTRAL | 2023-07-04 08:37:40 | 2023-07-04 08:37:49 | about 9s | `44653464` | `0x9399b7493668cde00743203de0e14095913c3b56cc417dca4f6819ccef9b01cb` |
| UPDOWN | 2023-07-04 08:43:38 | 2023-07-04 08:43:49 | about 11s | `44653618` | `0x426c5ad6caed2aeedcbebc9b47a37afbe4226fdd97c9571ad45d7ca9c54c42ac` |

- Polygon accepted both submissions before `SubmissionClosed`, and their CIDs
  remained the contracts' final submissions for the address.
- Both archives are now independently CID-verified, decrypt successfully, have
  the correct originator, and contain headerless two-column CSVs with exactly
  the 37 required unique symbols and numeric predictions.
- The address was the last submitter in both competitions. Every earlier valid
  challenge-8 submission reproduces its published score exactly; this is the
  only valid submission published as zero in either competition.
- The same address used the same headerless structure in challenges 9 and 10,
  where its scores and rewards reproduce exactly.
- All challenge-8 score, reward, and burn fields for the affected address were
  published as zero. The verifier computes negative rewards, which should have
  been represented as burns.

### Working explanation

The evidence is most consistent with an early backend version that was not
fully synchronized with the on-chain submission close time. It likely captured
or processed its submission set before the final on-chain close state. A second
possibility is RPC synchronization or indexing lag: a job reading `latest` state
or polling logs without first proving that its provider had reached the close
block could have missed the final `SubmissionUpdated` events. A third possibility
is a discrepancy between submission time and IPFS pinning, propagation, or
gateway availability. Any of these paths could have omitted these late CIDs and
caused the historical scorer to treat the staked address as having no usable
submission, which that code converted to a zero score and reward.

The short upload-to-inclusion gaps are normal: an archive must be uploaded before
its CID can be submitted, and the transaction is included several seconds later.
They show that the CIDs existed before their on-chain events, but not which IPFS
peers or gateways could retrieve them later. Conversely, the events were already
4m40s and 11m16s old at close, so a post-close backend using a sufficiently
synchronized RPC should have seen them. Missing both is therefore stronger
evidence for an early or stale submission snapshot than for CSV rejection.

This explanation is a strong inference, not a proven reconstruction: historical
backend logs, database rows, and IPFS provider logs would be needed to distinguish
an early snapshot, an RPC synchronization problem, and a retrieval failure.

### Expected backend behavior

Manual re-pinning by a participant should not be a prerequisite for scoring.
After the on-chain close, the backend should read the final submission CID for
every participant at an explicit block at or after `SubmissionClosed`. It should
first verify that the RPC provider has reached that block, wait the chosen number
of confirmations, and either read final contract state at that pinned block or
process submission logs through the close block. It should then retrieve every
final CID. IPFS can still be unavailable when no connected peer retains the
bytes, so retrieval is not guaranteed merely by the CID's presence on-chain. A
missing object must therefore trigger retries and an explicit failed/deferred
finalization; it must not silently become a zero score or reward.
