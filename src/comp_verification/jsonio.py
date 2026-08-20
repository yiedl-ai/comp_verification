"""Canonical JSON persistence for reproducible manifests."""

import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_canonical_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = canonical_json_bytes(value)
    if path.exists() and path.read_bytes() == rendered:
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(rendered)
    temporary.replace(path)
