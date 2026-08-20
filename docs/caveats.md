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
| 14 | NEUTRAL publication and scoring | Immutable results CID points to dataset 15; corrected CID is stored on-chain under information item 0 for the zero address | 1 | Accepted corrected reference; publication and scoring pass with caveat |
| 19 | NEUTRAL and UPDOWN scoring | Three addresses unexpectedly published as zero in both competitions | 6 | Open; raw mismatches remain failures pending historical evidence or adjudication |
| 28 | NEUTRAL publication and scoring | Results CID contains the challenge-29 RSA public key | 1 | Open; publication fails and scoring is blocked pending an authenticated correction |
| 33 | NEUTRAL scoring | Last valid submission was published as zero | 1 | Open; raw mismatch remains a failure pending historical evidence or adjudication |

## Challenge 33 NEUTRAL: last valid submission published as zero

Challenge 33 publication integrity passes. Every UPDOWN comparison and every
NEUTRAL comparison except address
`0xcf28560da27700098a0efcb3f5742169948892de` reproduces exactly. That address's
final NEUTRAL CID, `QmNxtJthPTUD17jZ8D3M6KU5tsxJe2DhrqszaUbF2rFdh6`, is
retrievable and CID-verified. It decrypts with the published key, authenticates
the expected originator, and contains all 37 required unique numeric predictions.
The verifier computes gain `0.009486158977163549505271207912` and reward
`9.362509`; the published values and on-chain reward are zero.

Polygon included the single NEUTRAL submission event in block `51558186` at
2023-12-26 00:35:54 UTC, 126 seconds before `SubmissionClosed` in block
`51558245`. It was the last NEUTRAL submission. The same address submitted even
later to UPDOWN, 45 seconds before close, and that score reproduces exactly.
This makes close timing alone insufficient to explain the discrepancy.

The remaining hypotheses are a transient NEUTRAL retrieval/decryption failure,
competition-specific production database state, or a NEUTRAL-only early
submission snapshot. Historical backend logs or database rows are needed to
distinguish them. The mismatch remains open and does not count as a pass.

## Challenge 28 NEUTRAL: results CID is the challenge 29 public key

Challenge 28 NEUTRAL records results CID
`QmUZ1n2BGvpoHJXGXnpBenXs92DKVczsvyMq51ksb8zzK2` and digest
`0x5c50e9901763a21fef577e09b6d0cad3fbceecf7d213be8eda2bf3cdc25202b1`.
The 450 CID-verified bytes (SHA-256
`87aa6fa9b96345d40f4b22f57f644a53a358f3011cd1a9d52c0d0e30a3f984c5`)
are a PEM RSA public key, not a results CSV. Both contracts record that exact
CID and digest as the challenge-29 public key.

The bad digest was published by transaction
`0x2f341b417bda5b9043cf4d2ce4251ba202f90d65f31a86701a5eba1883b4f96e`
in Polygon block `50438838` at 2023-11-27 04:34:43 UTC. Challenge 28
UPDOWN uses a different results CID and passes publication and scoring exactly.
NEUTRAL remains a publication failure with scoring blocked until a corrected
results file is located and authenticated, preferably through an on-chain
information entry like the accepted challenge-14 correction.

## Challenge 19: three addresses zeroed in both competitions

Challenge 19 publication integrity passes, and every score/reward comparison
except six reproduces exactly under the source-backed 34-symbol policy. The six
exceptions are the same three addresses in both NEUTRAL and UPDOWN:

| Address | NEUTRAL computed gain / reward | UPDOWN computed gain / reward | Published |
| --- | ---: | ---: | ---: |
| `0x04e1dd13ef029f573cf717f094a6b601b9e03550` | `0.01422048693024655747846137765` / `36.281150` | `-0.005672794361844497155731123354` / `-4.069715` | zero in both |
| `0x8a8e1c4e454e092fc19c6cca2034bd22b29781e7` | `0.009438761760350053711062086911` / `23.964147` | `0.01217711329458432853668738102` / `8.762258` | zero in both |
| `0xb294a5316e76e84649a3b8ff0ff6ef9788595bed` | `0.01340266107515869221179582362` / `33.822564` | `0.01125442513536465684334956285` / `8.046307` | zero in both |

All six final CIDs are retrievable, CID-verified, decrypt with the published
private keys, authenticate the expected originators, and contain valid
headerless 34-row predictions. Polygon included them between 00:38:45 and
00:42:45 UTC on 2023-09-19, roughly six days before results publication. Many
other 34-row submissions score exactly, and these three addresses also score
exactly in challenges 9–18. This rules out a general CSV format, basket-size,
address, or close-time explanation.

The remaining hypotheses are production-only submission-selection/database
state or a historical retrieval/decryption failure. One affected UPDOWN address
updated its CID twice; the other five address/competition pairs did not. The
cause remains unresolved without historical backend logs or database rows, so
these six comparisons remain failures and are not caveated passes.

## Challenge 18: 37-symbol validation with 34 realized targets

Challenge 18 is an exact pass, but its evidence captures a useful transition
detail. The submission policy still required the 37-symbol basket, while source
dataset 19 omitted ALGO, SOL, and SUSHI. The historical scorer right-joined
submissions to the available answer rows before allocation, so it scored the
remaining 34 symbols. The verifier reproduces that join and records the three
missing policy symbols in the derived price-fixture provenance.

## Challenge 14 NEUTRAL: results CID points to dataset 15

At observed Polygon block `92336519`, challenge 14 NEUTRAL records results CID
`QmNXo5RtUahWHGB578jmkSNK3GSyRxmjRkYUYqoCDosCVd` and digest
`0x02dad9a83f016fd3b4763359ed358478768387df48665531a68f993130f4a0f8`.
Those are exactly the CID and digest recorded for the challenge 15 dataset.

The bytes were independently downloaded and CID-verified. Their SHA-256 is
`1e1adbc58045f0032091792c01e77a26d015d614cd251750750231c3c705f6a7`.
They form a ZIP archive containing `dataset/train_dataset.csv`,
`dataset/validation_dataset.csv`, and a quickstart notebook—not a published
results CSV. The original reference is immutable because `updateResults` only
operates on the contract's current challenge.

### On-chain correction

On 2026-08-20 at 08:27:52 UTC, transaction
`0x7402cc20948758b15f1349fd8ac58bd6da5cbe9e3287d1c4eb4322047aded314`
succeeded in Polygon block `92339630`. It stored the corrected digest under:

- Challenge: `14`
- Participant: `0x0000000000000000000000000000000000000000`
- Information item: `0`
- Value/digest: `0x117437e277e8c038eacbd82f2d450f93bba41af12bacfdde8a96640748c2bd5a`
- Corrected CID: `QmPWnRa7W3xSVWm2ST5REBiAA8ebbSVdYeFuzSmjGYERzy`

The verifier reads that information value at the correction block, converts the
32-byte digest to CIDv0, and requires it to match the tracked corrected CID. The
corrected object is an 8,514-byte results CSV with SHA-256
`db64c4fc21a0124861881433f331cd19dc41f6f37d96847cc3ae22f1addfed4a`.
It contains all 81 challenge 14 NEUTRAL participants. Every address and stake
matches the pinned challenge snapshot, every reward and burn matches Polygon,
and independently recomputing all relative gains and six-decimal wallet rewards
produces exact zero deltas.

The original bad content reference remains visible as a raw historical error.
Because the replacement digest is now explicitly stored on-chain and the
replacement content passes publication and scoring verification, both audits
count as passes with this caveat.

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
