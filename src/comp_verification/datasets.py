"""Extract and verify the minimal realized-return fixtures used for scoring."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .jsonio import canonical_json_bytes


@dataclass(frozen=True)
class ExtractedPrices:
    scoring_challenge: int
    source_dataset_challenge: int
    source_cid: str
    source_member: str
    date: str
    rows: tuple[tuple[str, str], ...]

    def csv_bytes(self) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["date", "symbol", "return"])
        writer.writerows((self.date, symbol, value) for symbol, value in self.rows)
        return output.getvalue().encode("utf-8")

    def provenance(self, archive_sha256: str, member: zipfile.ZipInfo) -> dict[str, Any]:
        rendered = self.csv_bytes()
        return {
            "schema_version": 1,
            "scoring_challenge": self.scoring_challenge,
            "source_dataset_challenge": self.source_dataset_challenge,
            "source_cid": self.source_cid,
            "source_archive_sha256": archive_sha256,
            "source_member": self.source_member,
            "source_member_crc32": f"{member.CRC:08x}",
            "source_member_uncompressed_size": member.file_size,
            "date": self.date,
            "row_count": len(self.rows),
            "prices_sha256": hashlib.sha256(rendered).hexdigest(),
        }


def extract_latest_realized_returns(
    archive_path: Path,
    *,
    scoring_challenge: int,
    source_dataset_challenge: int,
    source_cid: str,
    symbols: tuple[str, ...] | None = None,
) -> tuple[ExtractedPrices, zipfile.ZipInfo]:
    symbol_filter = None if symbols is None else set(symbols)
    with zipfile.ZipFile(archive_path) as archive:
        member = _find_train_dataset(archive)
        with archive.open(member) as binary:
            text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            required = {"date", "symbol", "target_updown"}
            fields = set(reader.fieldnames or ())
            if not required <= fields:
                raise ValueError(
                    f"{member.filename} lacks required columns {sorted(required - fields)}"
                )
            latest_date: str | None = None
            latest_rows: dict[str, str] = {}
            for row in reader:
                date = (row.get("date") or "").strip()
                symbol = (row.get("symbol") or "").strip()
                value = (row.get("target_updown") or "").strip()
                if not date or not symbol or not value:
                    continue
                if symbol_filter is not None and symbol not in symbol_filter:
                    continue
                _validate_decimal(value, symbol)
                if latest_date is None or date > latest_date:
                    latest_date = date
                    latest_rows = {symbol: value}
                elif date == latest_date:
                    if symbol in latest_rows:
                        raise ValueError(f"duplicate symbol {symbol} on {date}")
                    latest_rows[symbol] = value
        if latest_date is None or not latest_rows:
            raise ValueError(f"no realized target rows found in {member.filename}")
        if symbols is not None and set(latest_rows) != symbol_filter:
            missing = sorted(symbol_filter - set(latest_rows))
            extra = sorted(set(latest_rows) - symbol_filter)
            raise ValueError(
                f"realized target basket mismatch; missing={missing}, extra={extra}"
            )
        return (
            ExtractedPrices(
                scoring_challenge=scoring_challenge,
                source_dataset_challenge=source_dataset_challenge,
                source_cid=source_cid,
                source_member=member.filename,
                date=latest_date,
                rows=tuple(sorted(latest_rows.items())),
            ),
            member,
        )


def write_price_fixture(
    prices: ExtractedPrices,
    member: zipfile.ZipInfo,
    archive_sha256: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    csv_bytes = prices.csv_bytes()
    destination.write_bytes(csv_bytes)
    destination.with_suffix(".json").write_bytes(
        canonical_json_bytes(prices.provenance(archive_sha256, member))
    )


def verify_price_fixture(
    prices: ExtractedPrices,
    member: zipfile.ZipInfo,
    archive_sha256: str,
    destination: Path,
) -> None:
    expected_csv = prices.csv_bytes()
    if not destination.exists():
        raise FileNotFoundError(destination)
    if destination.read_bytes() != expected_csv:
        raise ValueError(f"price fixture differs from source dataset: {destination}")
    provenance_path = destination.with_suffix(".json")
    expected_provenance = prices.provenance(archive_sha256, member)
    actual_provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if actual_provenance != expected_provenance:
        raise ValueError(f"price provenance differs from source dataset: {provenance_path}")


def _find_train_dataset(archive: zipfile.ZipFile) -> zipfile.ZipInfo:
    matches = [
        member
        for member in archive.infolist()
        if not member.is_dir()
        and member.filename.replace("\\", "/").endswith("dataset/train_dataset.csv")
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one dataset/train_dataset.csv, found {len(matches)}"
        )
    return matches[0]


def _validate_decimal(value: str, symbol: str) -> None:
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"invalid realized return for {symbol}: {value!r}") from error
    if not number.is_finite() or not math.isfinite(float(number)):
        raise ValueError(f"non-finite realized return for {symbol}: {value!r}")
