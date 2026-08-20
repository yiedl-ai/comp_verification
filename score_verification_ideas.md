# Score Verification Ideas and Considerations

## Objective

Build a public, independent verifier that starts from each participant's encrypted on-chain submission and proves whether the off-chain score and resulting reward or burn were computed correctly.

Comparing the published results CSV with contract state is useful, but it is only a publication-integrity check. The primary verification path must independently reconstruct the scoring inputs, execute the applicable historical policy, and compare the recomputed values with both IPFS and Polygon.

## What Was Studied

- Competition contracts at:
  - UPDOWN: `0xEcB9716867f9300F2706EdbB5b81c7a0AbDC5B29`
  - NEUTRAL: `0xC8519524013348466e18fC1747d11F1feA9473fd`
- The `competition` contract repository.
- The `competition_dataset_pipeline` main, extended, recovery, dynamic-basket, and HL-basket branches.
- Git history, reflogs, unreachable objects, scoring modules, basket code, settlement scripts, and existing verification scripts.
- On-chain challenge metadata, IPFS datasets, public/private keys, encrypted submissions, result files, historical stakes, rewards, and burns.

The current contracts began their challenge numbering in May 2023. Earlier 2021-2022 scoring commits belong to a predecessor era and must not be matched to these contracts merely by challenge number.

## Challenge 172 Proof of Concept

Challenge 172 was used to validate that independent submission-level verification is practical.

- Retrieved the challenge dataset, the following challenge's revealed answer data, the published private key, every submission CID, and both result CIDs from Polygon/IPFS.
- Successfully decrypted all 38 UPDOWN and 52 NEUTRAL submissions and verified each originator address.
- Reconstructed the challenge evaluation universe as 152 symbols: 153 configured symbols minus `TON`, which was absent from the finalized challenge intersection.
- Tested competing historical implementations against the published outputs:
  - legacy 77-symbol/raw-return policy;
  - 152-symbol intersection with raw-return NEUTRAL targets;
  - 152-symbol intersection with ranked NEUTRAL targets.
- The matching implementation used the 152-symbol intersection, raw realized targets for UPDOWN, and ranked targets for NEUTRAL.
- All 214 result rewards, including zero-score historical stakers, reproduced exactly at six-decimal token precision.
- Independently computed relative gains agreed with the published values up to implementation-level numeric noise (maximum observed difference approximately `5.11e-17`).
- All 92 UPDOWN and 122 NEUTRAL result rows also matched the contract's historical stake and reward/burn fields exactly.

This experiment demonstrates that published scores can act as an oracle for selecting the historical implementation when Git branches or possible uncommitted changes are ambiguous.

## Important Contract Semantics

Under the current wallet-return settlement model:

- A positive `wallet_reward` is recorded in the contract's legacy `challengeRewards` field.
- A negative `wallet_reward` is applied and recorded as `tokensBurned`.
- `challengeScores` and `tournamentScores` may remain zero even though a relative-gain score is published on IPFS.
- Result CSVs contain all historical stakers, not only successful submitters; non-submitters and invalid submissions generally receive score and reward zero.
- Historical stake must be read from `getStakedAmountForChallenge`, not reconstructed from the participant's current stake.

A verifier must encode these mappings explicitly instead of relying on the legacy field names.

## Historical Policy Reconstruction

The exact policy should be represented by a per-challenge registry, not inferred at runtime from a branch name. Initial evidence suggests these broad eras, but every boundary must be numerically confirmed:

- Challenges 1-53: approximately 37 required prediction symbols.
- Challenges 54-167: approximately 77 required prediction symbols.
- Challenges 168 onward: 153 configured symbols with a challenge-specific train/validation/answer intersection (152 in challenge 172), aliases, and competition-specific minimum overlap.

Policy dimensions that may need independent candidate versions include:

- required basket versus participant/basket intersection;
- symbol aliases and renames;
- handling of extra, missing, duplicate, malformed, NaN, or infinite rows;
- zero-exposure UPDOWN submissions;
- minimum NEUTRAL overlap and tied-rank behavior;
- raw versus ranked NEUTRAL targets;
- Decimal/float conversion, ranking implementation, and rounding;
- the answer workweek used at Monday settlement;
- stake snapshot source and block;
- dataset-generation behavior affecting the realized target rows.

For each challenge, candidate implementations should be executed against every submission. A policy is accepted only when it explains all published scores/rewards within declared tolerances. The registry should store the selected policy, supporting Git tree or recovered source, evidence, exceptions, and a confidence level.

## Recommended Product Shape

Use a GitHub repository as the source of truth, with a static website as the public interface.

### GitHub verifier

The repository should contain:

- a deterministic importable Python verifier;
- versioned policy modules and a challenge-to-policy registry;
- contract ABIs and chain/IPFS adapters;
- submission decryption and originator validation;
- deterministic normalization, allocation, scoring, and reward logic;
- per-challenge manifests and machine-readable audit reports;
- tests based on known historical challenges;
- a pinned runtime or container image;
- CI that reruns completed challenge audits and publishes artifacts.

The Python API should support full-challenge, single-competition,
single-participant, and publication-only verification. Notebooks and tests can
call the same API directly; the project does not need a CLI.

### Static website

The website should read generated audit artifacts rather than implement the authoritative scoring logic in JavaScript. It can provide:

- challenge and competition status;
- selected policy/version and evidence;
- input CIDs, blocks, basket, and target provenance;
- participant-level submission validity, allocation, score, reward, and differences;
- chain/IPFS/recomputation pass indicators;
- downloadable manifests, normalized inputs, and reports;
- exact reproduction code snippets.

This keeps the browser experience lightweight. For example, the challenge-173 dataset archive is about 1.04 GB and expands to roughly 8.5 GB, making full in-browser verification impractical.

### Spreadsheets

Excel or Google Sheets can be optional exports for participant-friendly inspection. They should not be authoritative because they are weak at preserving code versions, Decimal behavior, large datasets, encryption/decryption, reproducible environments, and tamper-evident provenance.

## Two Verification Levels

### Publication verification

This fast mode should:

1. Read the result CID and historical participant/staker sets from Polygon.
2. Fetch and validate the result file from IPFS.
3. Compare every result row with historical stake, positive reward, and burn fields.
4. Reconcile totals with contract events and transactions.

### Full computation verification

This authoritative mode should:

1. Resolve challenge open/close/settlement blocks and all relevant CIDs.
2. Fetch the challenge dataset and the dataset containing the revealed realized targets.
3. Fetch the revealed organizer private key after challenge closure.
4. Fetch and decrypt every submitted archive.
5. Verify the encrypted originator against the submitting address.
6. Apply the exact challenge-specific normalization and validity policy.
7. Reconstruct the evaluation basket and target vector.
8. Read the historical stake snapshot.
9. Recompute allocation, relative gain, and six-decimal reward/burn.
10. Compare recomputed output with the IPFS result and Polygon state.

## Per-Challenge Manifest

Each audit should produce a canonical manifest containing at least:

- chain ID and competition contract address;
- challenge number and series/workweek identifiers;
- open, close, result, payment, and burn blocks/transactions;
- dataset, public-key, private-key, submission, and result CIDs;
- exact evaluation symbols and aliases;
- answer dataset/date and target-vector hash;
- historical stake snapshot block and hash;
- selected policy ID, Git tree/commit, container digest, dependencies, and Decimal context;
- participant validity diagnostics and normalized-submission hashes;
- recomputed scores/rewards and observed IPFS/chain values;
- numeric tolerances and mismatch details;
- policy-selection evidence and confidence.

The manifest and reports should use deterministic serialization so their hashes are stable.

## Future Publishing Improvement

The current result CID points to a small results CSV. It proves which result bytes were published, but it does not commit to the code, policy, target vector, or normalized inputs that produced them.

For future challenges, publish a content-addressed audit bundle containing the result CSV and manifest, or add a dedicated on-chain audit-manifest CID/event. This should be designed with current result consumers in mind. The full dataset and original submissions can remain referenced by CID; the bundle should contain the small, exact scoring inputs and hashes needed for efficient review.

## Suggested Rollout

1. Turn the challenge-172 proof of concept into a deterministic library test fixture.
2. Implement the publication verifier for all completed challenges.
3. Add full recomputation for challenges 168 onward.
4. Numerically identify older policy boundaries by running candidate implementations against all submissions.
5. Record exceptions and confidence in the challenge registry.
6. Generate a static website from the verified reports.
7. Adopt a manifest/audit-bundle publishing step for future settlements before rewards are posted.

## Open Considerations

- Whether public audit artifacts may include decrypted participant predictions after the private key is revealed, or only hashes/derived allocations.
- Where large IPFS datasets should be cached for reliable CI without weakening CID verification.
- Whether an archival Polygon RPC is required for event/block reconstruction across every challenge.
- How to preserve exact historical Python/SciPy/Pandas behavior where tiny floating-point differences exist.
- Whether future settlement should require an independent verifier pass before submitting result/reward transactions.
- Whether policy confidence should distinguish exact source recovery from numerical behavioral reconstruction.
