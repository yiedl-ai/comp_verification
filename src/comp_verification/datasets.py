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


@dataclass(frozen=True)
class ExtractedTargets:
    """Lossless latest-date targets retained from one source dataset."""

    scoring_challenge: int
    source_dataset_challenge: int
    source_cid: str
    source_digest: str
    source_member: str
    date: str
    target_columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def csv_bytes(self) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("date", "symbol", *self.target_columns))
        writer.writerows((self.date, *row) for row in self.rows)
        return output.getvalue().encode("utf-8")

    def provenance(
        self,
        archive_sha256: str,
        archive_size: int,
        computed_source_cid: str,
        member: zipfile.ZipInfo,
    ) -> dict[str, Any]:
        rendered = self.csv_bytes()
        return {
            "schema_version": 1,
            "scoring_challenge": self.scoring_challenge,
            "source_dataset_challenge": self.source_dataset_challenge,
            "source_cid": self.source_cid,
            "source_digest": self.source_digest,
            "computed_source_cid": computed_source_cid,
            "source_cid_verified": computed_source_cid == self.source_cid,
            "source_archive_sha256": archive_sha256,
            "source_archive_size": archive_size,
            "source_member": self.source_member,
            "source_member_crc32": f"{member.CRC:08x}",
            "source_member_compressed_size": member.compress_size,
            "source_member_uncompressed_size": member.file_size,
            "date": self.date,
            "target_columns": list(self.target_columns),
            "row_count": len(self.rows),
            "targets_sha256": hashlib.sha256(rendered).hexdigest(),
        }


def extract_latest_targets(
    archive_path: Path,
    *,
    scoring_challenge: int,
    source_dataset_challenge: int,
    source_cid: str,
    source_digest: str,
) -> tuple[ExtractedTargets, zipfile.ZipInfo]:
    """Extract every symbol and target column from the archive's latest date."""

    with zipfile.ZipFile(archive_path) as archive:
        member = _find_train_dataset(archive)
        with archive.open(member) as binary:
            text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            fields = tuple(reader.fieldnames or ())
            required = {"date", "symbol", "target_updown"}
            missing = required - set(fields)
            if missing:
                raise ValueError(
                    f"{member.filename} lacks required columns {sorted(missing)}"
                )
            target_columns = tuple(
                column
                for column in ("target_updown", "target_neutral")
                if column in fields
            )
            latest_date: str | None = None
            latest_rows: dict[str, tuple[str, ...]] = {}
            for row in reader:
                date = (row.get("date") or "").strip()
                if not date:
                    continue
                symbol = (row.get("symbol") or "").strip()
                if not symbol:
                    raise ValueError(f"blank symbol on {date} in {member.filename}")
                values = tuple((row.get(column) or "").strip() for column in target_columns)
                for column, value in zip(target_columns, values, strict=True):
                    if value:
                        _validate_decimal(value, f"{symbol} {column}")
                if latest_date is None or date > latest_date:
                    latest_date = date
                    latest_rows = {symbol: values}
                elif date == latest_date:
                    if symbol in latest_rows:
                        raise ValueError(f"duplicate symbol {symbol} on {date}")
                    latest_rows[symbol] = values
        if latest_date is None or not latest_rows:
            raise ValueError(f"no target rows found in {member.filename}")
        rows = tuple(
            (symbol, *latest_rows[symbol]) for symbol in sorted(latest_rows)
        )
        return (
            ExtractedTargets(
                scoring_challenge=scoring_challenge,
                source_dataset_challenge=source_dataset_challenge,
                source_cid=source_cid,
                source_digest=source_digest,
                source_member=member.filename,
                date=latest_date,
                target_columns=target_columns,
                rows=rows,
            ),
            member,
        )


def write_target_fixture(
    targets: ExtractedTargets,
    member: zipfile.ZipInfo,
    archive_sha256: str,
    archive_size: int,
    computed_source_cid: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(targets.csv_bytes())
    destination.with_suffix(".json").write_bytes(
        canonical_json_bytes(
            targets.provenance(
                archive_sha256,
                archive_size,
                computed_source_cid,
                member,
            )
        )
    )


def verify_target_fixture(
    targets: ExtractedTargets,
    member: zipfile.ZipInfo,
    archive_sha256: str,
    archive_size: int,
    computed_source_cid: str,
    destination: Path,
) -> None:
    if destination.read_bytes() != targets.csv_bytes():
        raise ValueError(f"target fixture differs from source dataset: {destination}")
    provenance_path = destination.with_suffix(".json")
    actual = json.loads(provenance_path.read_text(encoding="utf-8"))
    expected = targets.provenance(
        archive_sha256,
        archive_size,
        computed_source_cid,
        member,
    )
    if actual != expected:
        raise ValueError(f"target provenance differs from source dataset: {provenance_path}")


def derive_price_fixture_from_targets(
    source: Path,
    *,
    symbols: tuple[str, ...],
    policy_id: str,
    destination: Path,
    target_column: str = "target_updown",
    source_reference: str | None = None,
    require_all_symbols: bool = True,
) -> dict[str, Any]:
    """Materialize a scorer-sized basket from a verified condensed target fixture."""

    provenance_path = source.with_suffix(".json")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    source_bytes = source.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if source_sha256 != provenance.get("targets_sha256"):
        raise ValueError(f"target fixture hash differs from provenance: {source}")
    if provenance.get("source_cid_verified") is not True:
        raise ValueError(f"target fixture source CID is not verified: {source}")
    if target_column not in provenance.get("target_columns", []):
        raise ValueError(f"target fixture lacks {target_column}: {source}")

    reader = csv.DictReader(io.StringIO(source_bytes.decode("utf-8-sig")))
    fields = set(reader.fieldnames or ())
    required = {"date", "symbol", target_column}
    if not required <= fields:
        raise ValueError(f"target fixture lacks columns {sorted(required - fields)}")
    allowed = set(symbols)
    rows: dict[str, str] = {}
    dates: set[str] = set()
    for row in reader:
        symbol = (row.get("symbol") or "").strip()
        if symbol not in allowed:
            continue
        if symbol in rows:
            raise ValueError(f"duplicate target symbol {symbol}: {source}")
        value = (row.get(target_column) or "").strip()
        _validate_decimal(value, symbol)
        rows[symbol] = value
        dates.add((row.get("date") or "").strip())
    missing = sorted(allowed - set(rows))
    if missing and require_all_symbols:
        raise ValueError(f"target fixture is missing policy symbols: {missing}")
    if not rows:
        raise ValueError(f"target fixture has no policy symbols: {source}")
    if dates != {provenance.get("date")}:
        raise ValueError(f"target fixture date differs from provenance: {source}")

    prices = ExtractedPrices(
        scoring_challenge=int(provenance["scoring_challenge"]),
        source_dataset_challenge=int(provenance["source_dataset_challenge"]),
        source_cid=str(provenance["source_cid"]),
        source_member=str(provenance["source_member"]),
        date=str(provenance["date"]),
        rows=tuple((symbol, rows[symbol]) for symbol in sorted(rows)),
    )
    rendered = prices.csv_bytes()
    derived_provenance = {
        "schema_version": 1,
        "scoring_challenge": prices.scoring_challenge,
        "source_dataset_challenge": prices.source_dataset_challenge,
        "source_cid": prices.source_cid,
        "source_archive_sha256": provenance["source_archive_sha256"],
        "source_member": prices.source_member,
        "source_member_crc32": provenance["source_member_crc32"],
        "source_member_uncompressed_size": provenance[
            "source_member_uncompressed_size"
        ],
        "date": prices.date,
        "row_count": len(prices.rows),
        "prices_sha256": hashlib.sha256(rendered).hexdigest(),
        "derived_from": source.name if source_reference is None else source_reference,
        "derived_from_targets_sha256": source_sha256,
        "target_column": target_column,
        "policy_id": policy_id,
        "missing_policy_symbols": missing,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(rendered)
    destination.with_suffix(".json").write_bytes(
        canonical_json_bytes(derived_provenance)
    )
    return derived_provenance


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
