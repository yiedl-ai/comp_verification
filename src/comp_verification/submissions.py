"""Decrypt participant archives and normalize their prediction CSVs."""

from __future__ import annotations

import io
import math
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_string_dtype


class InvalidSubmission(ValueError):
    pass


@dataclass(frozen=True)
class DecryptedSubmission:
    address: str
    originator: str
    predictions_csv: bytes
    prediction_member: str
    key_member: str


def decrypt_submission_archive(
    archive_path: Path, private_key_path: Path, expected_address: str
) -> DecryptedSubmission:
    with zipfile.ZipFile(archive_path) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        key_members = [member for member in members if member.filename.lower().endswith(".pem")]
        originator_members = [
            member
            for member in members
            if Path(member.filename).name.lower() == "originator.bin"
        ]
        prediction_members = [
            member
            for member in members
            if member.filename.lower().endswith(".bin")
            and Path(member.filename).name.lower() != "originator.bin"
        ]
        if len(key_members) != 1:
            raise InvalidSubmission(f"expected one encrypted key, found {len(key_members)}")
        if len(originator_members) != 1:
            raise InvalidSubmission(
                f"expected one encrypted originator, found {len(originator_members)}"
            )
        if len(prediction_members) != 1:
            raise InvalidSubmission(
                f"expected one encrypted prediction, found {len(prediction_members)}"
            )

        private_key = RSA.import_key(private_key_path.read_bytes())
        symmetric_key = PKCS1_OAEP.new(private_key).decrypt(archive.read(key_members[0]))
        originator = _decrypt_aes_gcm(
            archive.read(originator_members[0]), symmetric_key
        ).decode("utf-8").strip().lower()
        expected = expected_address.lower()
        if originator != expected:
            raise InvalidSubmission(
                f"originator {originator!r} does not match submitter {expected!r}"
            )
        predictions = _decrypt_aes_gcm(
            archive.read(prediction_members[0]), symmetric_key
        )
        return DecryptedSubmission(
            address=expected,
            originator=originator,
            predictions_csv=predictions,
            prediction_member=prediction_members[0].filename,
            key_member=key_members[0].filename,
        )


def parse_predictions(
    predictions_csv: bytes,
    symbols: tuple[str, ...],
    *,
    reject_duplicates: bool = True,
) -> dict[str, Decimal]:
    try:
        frame = pd.read_csv(io.BytesIO(predictions_csv), header=None, index_col=None)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as error:
        raise InvalidSubmission("prediction CSV could not be parsed") from error
    frame.dropna(inplace=True)
    if frame.shape[1] != 2:
        raise InvalidSubmission("prediction CSV must contain exactly two columns")
    if len(frame) and frame.iloc[0, 0] == "symbol":
        if frame.iloc[0, 1] != "prediction":
            raise InvalidSubmission(
                f"unexpected prediction header: {frame.iloc[0].tolist()!r}"
            )
        frame = pd.read_csv(
            io.BytesIO(predictions_csv),
            header=None,
            index_col=None,
            skiprows=[0],
        )
        frame.dropna(inplace=True)
    if len(frame) == 0:
        raise InvalidSubmission("prediction CSV has no usable rows")
    if not is_string_dtype(frame.iloc[:, 0]) or not is_numeric_dtype(
        frame.iloc[:, 1]
    ):
        raise InvalidSubmission("prediction CSV has incorrect column types")

    parsed: dict[str, Decimal] = {}
    duplicates: set[str] = set()
    allowed = set(symbols)
    for raw_symbol, raw_value in frame.itertuples(index=False, name=None):
        symbol = str(raw_symbol).strip()
        if not symbol:
            continue
        if symbol not in allowed:
            continue
        if symbol in parsed:
            duplicates.add(symbol)
        try:
            as_float = float(raw_value)
        except (TypeError, ValueError) as error:
            raise InvalidSubmission(f"non-numeric prediction for {symbol}") from error
        if not math.isfinite(as_float):
            raise InvalidSubmission(f"non-finite prediction for {symbol}")
        parsed[symbol] = Decimal(str(raw_value))

    if reject_duplicates and duplicates:
        raise InvalidSubmission(f"duplicate prediction symbols: {sorted(duplicates)}")
    missing = [symbol for symbol in symbols if symbol not in parsed]
    if missing:
        raise InvalidSubmission(f"missing prediction symbols: {missing}")
    return {symbol: parsed[symbol] for symbol in symbols}


def _decrypt_aes_gcm(blob: bytes, key: bytes) -> bytes:
    if len(blob) < 32:
        raise InvalidSubmission("encrypted AES-GCM payload is too short")
    nonce, ciphertext, tag = blob[:16], blob[16:-16], blob[-16:]
    try:
        return AES.new(key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(ciphertext, tag)
    except ValueError as error:
        raise InvalidSubmission("AES-GCM authentication failed") from error
