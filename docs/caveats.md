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
| 40–42 | NEUTRAL and UPDOWN publication/scoring | Mistaken settlement, exact undo, corrected 30-symbol settlement | 8 | Accepted as one correction sequence; raw metadata irregularities remain visible |
| 52 | NEUTRAL and UPDOWN scoring | Production switched to the 77-symbol basket one challenge before the recoverable repository history indicates | 0 | Exact recovered-policy pass; inference is retained in every scoring report |
| 73 | NEUTRAL scoring | One valid, early submission was published as zero | 1 | Open; raw mismatch remains a failure pending historical retrieval/database evidence |
| 94 | UPDOWN submission/scoring | One on-chain submission digest is ASCII hex text rather than a raw SHA-256 digest and its derived CID is unavailable | 0 | Scoring passes; the unverifiable submission is explicitly retained as unavailable |
| 95 | NEUTRAL submission/scoring | One on-chain submission digest is ASCII hex text rather than a raw SHA-256 digest and its derived CID is unavailable | 0 | Scoring passes; the unverifiable submission is explicitly retained as unavailable |
| 110 | UPDOWN publication/scoring | Result CID is the challenge-109 UPDOWN file | 1 | All on-chain rewards reproduce exactly; relative-gain publication remains open |
| 113 | NEUTRAL and UPDOWN publication/scoring | Production used `HAI=1` instead of the raw `21.227900966966708`; UPDOWN result CID is stale | 1 | NEUTRAL scores/rewards and UPDOWN on-chain rewards reproduce exactly; UPDOWN score publication remains open |
| 116 | UPDOWN publication/scoring | Challenge-116 CID is challenge 115's file; the correct file appears under challenge 117 | 1 | All scores/rewards reproduce exactly through the late file; challenge association remains open |
| 117 | NEUTRAL and UPDOWN publication/scoring | Both result CIDs contain exact challenge-116 files | 2 | All challenge-117 on-chain rewards reproduce exactly; challenge-117 relative-gain publication remains open |
| 129 | NEUTRAL and UPDOWN publication/scoring | Each result omits two malformed, zero-stake submitters | 4 | Every published score/reward and every wallet outcome reproduce exactly; raw row-completeness failures remain visible |

## Challenge 110: stale UPDOWN result reference

Challenge 110 UPDOWN records CID
`QmYuTvKSdD7k5A8UNM75HDume1o17BeQ5VL97CP56bitsX` (SHA-256
`39904611242dc0d500cc3be2f2609195289a4ea0933f1471f107ea356d8d07bf`).
Those bytes are exactly challenge 109's UPDOWN file and every row embeds
challenge `109`. They are not merely mislabeled challenge-110 results:
comparing the file to challenge 110's chain snapshot produces 77
stake/reward/burn field mismatches.

The calculation itself is recoverable. All 51 valid NEUTRAL scores and rewards
reproduce exactly from the CID-verified dataset and submissions. For UPDOWN,
the same historical scorer reproduces the net on-chain reward of every one of
the 38 valid submissions exactly. The verifier therefore records reward
verification separately, but leaves UPDOWN relative-gain publication open and
failed until an authenticated challenge-110 result file is recovered.

## Challenge 113: HAI target override and stale UPDOWN result reference

Dataset 114 is CID-verified and records challenge 113's `HAI` values as
`target_updown=21.227900966966708` and `target_neutral=1.0`. The recoverable
scorer using the raw `target_updown` value mismatches all 44 valid NEUTRAL
submissions and 40 of 42 nonzero UPDOWN rewards. This is not a broad policy or
basket mismatch. Solving the combined scoring equations gives a unique
77-symbol return vector: 86 equations have rank 77, and the inferred vector
matches every raw `target_updown` value except `HAI`, where it is exactly `1`.

Applying only `HAI=1` through a separate historical scoring override reproduces
all 44 published NEUTRAL relative gains and rewards exactly, with zero tolerance.
It also reproduces all 42 UPDOWN on-chain net rewards exactly. The committed
price fixture remains the unedited value derived from the CID-verified dataset;
the override is explicit in code and in each affected scoring report.

UPDOWN has a separate publication defect. Challenge 113 records result CID
`QmWXyyvUsNw5XfDbzknq7knGUsNohPMABqB5crNwRirskY` (SHA-256
`3123b802b6d8052bf2140f56bef22cabfd454f196d6a522f9b354b68c52ac7f8`),
which is exactly challenge 112's UPDOWN result file and embeds challenge `112`.
It does not describe challenge 113: comparing its stake/reward/burn fields to
the challenge-113 chain snapshot produces 123 field mismatches. The verifier
therefore reports challenge-113 UPDOWN rewards as exactly verified directly
against chain, while leaving relative-gain publication open and failed until an
authenticated challenge-113 UPDOWN result file is recovered.

## Challenge 116: stale UPDOWN result reference

Challenge 116 UPDOWN records CID
`QmQFS2AEcbmGCWvJSvi78neiLCCaCgfxuMSFAUNx6YUwuQ` (SHA-256
`cd02bebbda59676615bc7e571fe3242a8a67e151ae4ae95dba6227627f7cdae6`).
Those bytes are exactly challenge 115's UPDOWN result file and every row embeds
challenge `115`. Comparing that prior file with challenge 116's chain snapshot
produces 90 stake/reward/burn field mismatches, so it cannot stand in as a
mislabeled challenge-116 result.

The correct challenge-116 UPDOWN file appears one challenge late, under
challenge 117, at CID `QmSBwXPHHSQcVjR8ZuqxuXvWqBadQgGEQfUbZm3YVSpkj4`.
It matches all 90 challenge-116 chain rows and all independently recomputed
relative gains exactly. Thus all 51 valid NEUTRAL and 38 valid UPDOWN scores and
rewards reproduce exactly. The verifier resolves scoring through this late,
on-chain-authenticated file while retaining the challenge-116 publication-link
failure and caveat.

## Challenge 117: both result references are one challenge late

Both challenge-117 result references contain challenge `116`, not challenge
`117`. The NEUTRAL CID
`QmQW16CZjTTL25jpPkA4B4y9jF9UxNL4gpF4r5xscZcDeT` (SHA-256
`7a724e1602460f3071ca04402397acf94ac783b94823721e3f4bf9bcf3370de4`)
is exactly the already-published challenge-116 NEUTRAL file. The UPDOWN CID
`QmSBwXPHHSQcVjR8ZuqxuXvWqBadQgGEQfUbZm3YVSpkj4` (SHA-256
`bbf1e4683be3325628969da4638f9c0cdaf04c8eca9a33f7c08f4985d9107951`)
is the missing correct challenge-116 UPDOWN file: it matches challenge 116's 90
chain participants in every stake/reward/burn field, and all 90 relative gains
match independent challenge-116 recomputation exactly.

Neither file describes challenge 117. Comparing them with the challenge-117
chain snapshot produces 130 NEUTRAL and 99 UPDOWN stake/reward/burn field
mismatches. Nevertheless, independent recomputation from dataset 118 and the
challenge-117 submissions matches every challenge-117 net on-chain reward:
54 valid NEUTRAL and 43 valid UPDOWN submissions. The reward layer therefore
passes, while both challenge-117 relative-gain publications remain open.

## Challenge 129: invalid zero-financial submitters omitted from results

Both challenge-129 result files are internally correct and match every included
chain stake/reward/burn value. NEUTRAL omits addresses
`0x93d523c427aea3a50c9499e544eacff9bdc7820d` and
`0xa3b020f048bbe1dd970dcdb85dfc780c2ecd7131`; UPDOWN omits the first address
and `0xf44fa9622f736d1443bec6828eadc50c393e93f6`. Each omitted submission is
malformed (not a two-column prediction CSV), and each participant has exactly
zero historical stake, challenge reward, and burn.

The verifier retains the four raw result-row omissions in the publication
reports. In scoring, it treats an omitted row as an implicit zero only when the
submission is independently invalid or unavailable and all three financial
amounts are zero. A valid, staked, rewarded, or burned omission still fails.
Under that narrow rule, all 51 valid NEUTRAL and 38 valid UPDOWN scores and
rewards reproduce exactly, as do the four zero wallet outcomes.

## Challenge 94 UPDOWN: malformed, unavailable submission reference

Address `0x81fbfb07888fff733958210796af7cbe4368ae5f` records submission CID
`QmV5kHQxmPCU9XmsX973z3HoQK2znnp7bHX78o3S8Q4nLC`. The underlying on-chain
bytes32 value is
`0x6430663139613065343431326466613334373630356638636666356335376335`,
which decodes to the 32 ASCII characters `d0f19a0e4412dfa347605f8cff5c57c5`
rather than a raw 32-byte SHA-256 digest. The derived CID remained unavailable
through the authenticated gateway and independent public gateway probes.

The historical result and on-chain reward are both zero for this address.
Treating the unusable reference as unavailable reproduces every challenge-94
score and reward exactly: all 69 NEUTRAL submissions and 51 other UPDOWN
submissions validate and score normally. The same address repeated this exact
encoding category in challenge 95 NEUTRAL, strongly indicating a participant
client encoding defect rather than an off-chain scoring discrepancy.

## Challenge 95 NEUTRAL: malformed, unavailable submission reference

Address `0x81fbfb07888fff733958210796af7cbe4368ae5f` records submission CID
`QmV2buxsDmVkTGGNin4KQDWR8bU4XDpnDSfTJeiARcrocs`. The underlying on-chain
bytes32 value is
`0x6362316664633765333834303066373936363330376132656531663461326430`,
which decodes to the 32 ASCII characters `cb1fdc7e38400f7966307a2ee1f4a2d0`
rather than a raw 32-byte SHA-256 digest. This is consistent with a client
accidentally storing textual hex in bytes32.

The derived CID remained unavailable after all configured authenticated-gateway
attempts, so the verifier cannot inspect or score any intended file. The
historical result and on-chain reward are both zero for this address. Treating
the unusable final on-chain reference as unavailable reproduces every challenge
95 score and reward exactly: 70 other NEUTRAL submissions and 49 UPDOWN
submissions validate and score normally. The challenge therefore passes with an
explicit verification limitation, not an accepted mismatch.

## Challenge 73 NEUTRAL: valid submission published as zero

Challenge 73 publication integrity passes, and all UPDOWN comparisons and all
but one NEUTRAL comparison reproduce exactly. Address
`0x43b7a5912528434aa27163feb26dd586d488abf8` has final submission CID
`QmXFWqVuLEvqRwtv7RQyczJRHGWQ8agzCejXpRVmE2mmgK`, but its published gain and
reward are zero. The verifier computes gain
`-0.04071256664702073565995035846` and reward `-4.071257`, which should have
been recorded as a burn.

The archive is CID-verified (SHA-256
`e51ef239a913aadfb33cc834e7a22d3af391563a352dea8faef607ecc8c89a44`),
decrypts with the published private key, authenticates the expected originator,
and contains a readable two-column CSV. After the same `dropna` behavior as the
historical backend, its 1,621 unique non-null symbols include every required
77-symbol policy asset exactly once and numeric predictions. The encrypted
prediction member is named `20240916_predictions.bin`; the recovered production
retrieval code accepts any non-originator `.bin`, so that filename is not a
rejection explanation.

Polygon included the submission in block `61904152` at 2024-09-16 18:10:10 UTC,
transaction `0x8477a977a61d3f4daf4c72cd1968e383aae0da1b4f548fbc4002e52284043c5b`.
NEUTRAL closed in block `61915449` at 2024-09-17 00:57:12 UTC, 6h47m02s later;
three other submissions followed this one. This rules out a close-boundary
race. A transient IPFS retrieval/decryption failure or production database
insertion/state issue remains plausible, but historical backend logs are needed
to prove the cause. The mismatch remains open.

## Challenge 52: production-only 77-symbol policy cutover

The repository chronology initially placed the 30-to-77-symbol transition at
challenge 53. That policy mismatches all 53 nominally valid NEUTRAL submissions
and all 48 nominally valid UPDOWN submissions in challenge 52. Reprocessing the
same CID-verified submissions with the 77-symbol parser leaves 36 valid NEUTRAL
and 32 valid UPDOWN submissions and reproduces every published gain and reward
exactly, with zero tolerance.

Challenge 51 remains an exact 30-symbol reproduction, while challenge 52 is an
exact 77-symbol reproduction. The numerical boundary is therefore definitive:
production switched at challenge 52. Because the recoverable source commit
would otherwise imply challenge 53, the most likely explanation is the
production-only or uncommitted scoring change anticipated by this audit. This
does not excuse or alter any result; it records the recovered policy required to
verify that the challenge-52 off-chain computation was correct.

## Challenges 40–42: mistake, undo, and corrected settlement

Challenges 40, 41, and 42 must be audited as one accounting sequence. Challenge
40 posted the mistaken original rewards. Challenge 41 reversed every challenge-40
net reward exactly, address by address and in both competitions. Challenge 42
then posted the corrected rewards. The user explicitly confirmed these three
roles, and the chain values prove the undo independently.

The underlying mistake coincides with the production transition from 37 to 30
symbols. Fifteen NEUTRAL and nine UPDOWN challenge-40 submissions contain exactly
the new 30-symbol basket, omitting `1INCH`, `CELO`, `ENJ`, `SNX`, `UMA`, `ZEC`,
and `ZRX`; the ordinary 37-symbol backend treated them as invalid and published
zeros. Re-decrypting all challenge-40 submissions and applying the 30-symbol
policy reproduces the corrected challenge-42 files exactly: 57 valid NEUTRAL
and 51 valid UPDOWN submissions, with zero score or reward deltas. The one other
submitted file in each competition has the wrong second-column header
(`target_neutral` or `target_updown` instead of `prediction`) and correctly
remains zero.

The challenge-42 CSVs intentionally retain embedded challenge `40` and the
original challenge-40 stakes because they settle the original submissions.
Every published wallet reward equals challenge 42's on-chain reward minus burn.
Two participants changed stake by challenge 42; those two raw stake-field
differences are retained but do not affect the corrected calculation.

The supplied historical export function corroborates this treatment: for
challenge 41 it unions `getAllSubmitters(40)` with `getAllSubmitters(41)`, and
for challenge 42 it unions `getAllSubmitters(40)` with
`getAllSubmitters(42)`. The SHA-256 of the supplied 207-line reference is
`cba7659bc0de0bcd1e7aec2e81d03df6c0a9200eb8138818108f673497a7c0c5`.
The verifier records a dedicated correction report for each competition and
counts the sequence as passed with this caveat.

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
