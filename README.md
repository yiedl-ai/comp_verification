# Competition verification

Independent Python code for reproducing Yiedl competition scores and rewards
from Polygon and IPFS evidence.

The completed scoring audit currently covers challenges 1–15. It stores raw
IPFS downloads in the ignored `.cache/` directory and commits only the small
price/target extracts needed by the scorer under `data/prices/` and
`data/targets/`.

## Setup

```bash
uv sync
cp config.example.toml config.toml
```

Put the Polygon RPC URL in the ignored `config.toml`. RPC retries, JSON batch
size/rate, multicall size, log block span, IPFS retries, chunk size, and download
concurrency are all configurable there.

There is intentionally no CLI. Use the Python API from a notebook, test, or
short `uv run python` session:

```python
from pathlib import Path

from comp_verification.workflow import FirstTenWorkflow
from comp_verification.ipfs import print_download_progress

workflow = FirstTenWorkflow.from_config(Path.cwd())
workflow.ingest_chain()
workflow.verify_chain()
workflow.ingest_chain_events()
workflow.verify_chain_events()
workflow.download_datasets(progress=print_download_progress)
workflow.extract_prices(progress=print_download_progress)
workflow.verify_prices(progress=print_download_progress)
workflow.verify_publication(progress=print_download_progress)
workflow.ingest_submissions(progress=print_download_progress)
workflow.audit_scoring()
workflow.build_summary()
workflow.build_audit_status()
```

`ingest_chain()` records on-chain dataset, result, private-key, submission,
stake, reward, and burn observations. Dataset extraction is separate: scoring
challenge `n` uses the realized target rows revealed in dataset `n + 1`.
The verifier deliberately uses the historical pandas float-ingestion semantics
before Decimal scoring. Relative gains and six-decimal rewards must both match
exactly; the audit tolerance is zero. Python 3.11, pandas 1.5.3, and NumPy
1.24.4 are pinned by `uv` because later parser versions can produce different
binary floats for the same decimal text.

Tracked chain snapshots are pinned to an explicit historical block.
`verify_chain()` re-queries every field at that same block and writes an exact
comparison under `reports/chain/`; `ingest_chain_events()` records the relevant
lifecycle events with their block hashes and transaction hashes under
`manifests/chain-events/`. `verify_chain_events()` independently re-queries and
compares those raw event records.

`build_summary()` writes `reports/first-ten-summary.json`, retaining detailed
participant mismatches and their submission block/transaction provenance.
Known limitations and historical operational explanations are maintained in the
central [`docs/caveats.md`](docs/caveats.md) register. Generated reports link to
applicable entries. Raw mismatches remain visible; only an explicit accepted
adjudication in `problems/register.json` can count one as a caveated pass.
`reports/audit-status.md` is the generated repository-wide audit table.

Historical result hashes cannot be changed after a later challenge opens. When
an accepted correction exists under the challenge's zero-address information
entry, its pinned evidence is stored in `manifests/corrections/`. Publication
verification re-reads the information value at the correction block, derives
the corrected CID, and retains both the immutable original CID and the resolved
CID in its report. Challenge 14 NEUTRAL is the first such correction.

For the full historical evidence range, use `EvidenceWorkflow`. Its bounds come
from `[scope]` in `config.toml`; the current configuration indexes challenges and
datasets 1–173 and marks scoring challenges 1–172 as dataset-ready. The bounded
dataset path is:

```python
from pathlib import Path

from comp_verification import EvidenceWorkflow
from comp_verification.ipfs import print_download_progress

evidence = EvidenceWorkflow.from_config(Path.cwd())
evidence.ingest_dataset_catalog()
evidence.ingest_chain_snapshots()
evidence.condense_score_ready_datasets(
    progress=print_download_progress,
    prune_raw=True,
)
```

Condensation handles one archive at a time, verifies its on-chain digest and
UnixFS CID, preserves every latest-date symbol plus both target columns, writes
archive/member/hash provenance, independently re-extracts the fixture, and only
then permits deletion of that exact cache file and completion marker.
