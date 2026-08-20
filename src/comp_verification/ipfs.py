"""Resumable IPFS gateway downloads into the ignored local cache."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .encoding import single_block_file_cid_v0


_UNIXFS_BLOCK_SIZE = 256 * 1024


class IpfsDownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadedArtifact:
    cid: str
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class DownloadProgress:
    cid: str
    downloaded: int
    total: int | None
    complete: bool


ProgressCallback = Callable[[DownloadProgress], None]
_DISPLAY_STATE: dict[str, tuple[int, float]] = {}


class IpfsGateway:
    def __init__(
        self,
        base_url: str,
        cache: Path,
        *,
        user_agent: str = "comp-verification/0.1",
        timeout: float = 120,
        attempts: int = 5,
        retry_base_delay: float = 2.0,
        chunk_size: int = 1024 * 1024,
        max_concurrent_downloads: int = 8,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache = cache
        self.user_agent = user_agent
        self.timeout = timeout
        self.attempts = attempts
        self.retry_base_delay = retry_base_delay
        self.chunk_size = chunk_size
        self.max_concurrent_downloads = max_concurrent_downloads

    def download(
        self,
        cid: str,
        *,
        progress: ProgressCallback | None = None,
        expected_sha256: str | None = None,
    ) -> DownloadedArtifact:
        if not cid:
            raise ValueError("CID must not be empty")
        self.cache.mkdir(parents=True, exist_ok=True)
        destination = self.cache / cid
        partial = destination.with_suffix(".part")
        marker = destination.parent / f"{destination.name}.complete"
        if destination.exists() and not _completion_marker_matches(destination, marker):
            if expected_sha256 and _sha256_file(destination) == expected_sha256:
                _write_completion_marker(destination, marker, expected_sha256)
            elif _single_block_cid_matches(destination, cid):
                _write_completion_marker(destination, marker)
            else:
                remote_size = self._remote_size(cid)
                local_size = destination.stat().st_size
                if local_size == remote_size:
                    _write_completion_marker(destination, marker)
                elif local_size < remote_size and not partial.exists():
                    destination.replace(partial)
                elif local_size < remote_size:
                    raise IpfsDownloadError(
                        f"both incomplete final and partial files exist for {cid}"
                    )
                else:
                    raise IpfsDownloadError(
                        f"cached file for {cid} is larger than gateway content"
                    )
        if not destination.exists():
            last_error: IpfsDownloadError | None = None
            for attempt in range(self.attempts):
                try:
                    self._download_to_partial(cid, partial, progress)
                    last_error = None
                    break
                except IpfsDownloadError as error:
                    last_error = error
                    if attempt + 1 < self.attempts:
                        time.sleep(self.retry_base_delay * 2**attempt)
            if last_error is not None:
                raise last_error
            partial.replace(destination)
            _write_completion_marker(destination, marker)
        artifact = DownloadedArtifact(
            cid=cid,
            path=destination,
            size=destination.stat().st_size,
            sha256=_sha256_file(destination),
        )
        if artifact.size <= _UNIXFS_BLOCK_SIZE and not _single_block_cid_matches(
            destination, cid
        ):
            raise IpfsDownloadError(f"cached bytes do not match CIDv0 {cid}")
        if expected_sha256 and artifact.sha256 != expected_sha256:
            raise IpfsDownloadError(
                f"cached SHA-256 differs from recorded evidence for {cid}"
            )
        if progress is not None:
            progress(DownloadProgress(cid, artifact.size, artifact.size, True))
        return artifact

    def _remote_size(self, cid: str) -> int:
        request = Request(
            f"{self.base_url}/{cid}",
            headers={
                "Accept": "application/octet-stream",
                "Range": "bytes=0-0",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                total = _response_total(response, 0)
                if total is None:
                    raise IpfsDownloadError(
                        f"gateway did not report content length for {cid}"
                    )
                response.read(1)
                return total
        except (HTTPError, URLError, TimeoutError) as error:
            raise IpfsDownloadError(f"failed to inspect remote size for {cid}") from error

    def download_many(
        self,
        cids: list[str] | set[str],
        *,
        progress: ProgressCallback | None = None,
    ) -> list[DownloadedArtifact]:
        ordered = sorted(set(cids))
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            artifacts = list(
                executor.map(
                    lambda cid: self.download(cid, progress=progress),
                    ordered,
                )
            )
        return artifacts

    def _download_to_partial(
        self,
        cid: str,
        partial: Path,
        progress: ProgressCallback | None,
    ) -> None:
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {
            "Accept": "application/octet-stream",
            "User-Agent": self.user_agent,
        }
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = Request(f"{self.base_url}/{cid}", headers=headers)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                if offset and status == 206:
                    mode = "ab"
                    downloaded = offset
                elif status == 200:
                    mode = "wb"
                    downloaded = 0
                else:
                    raise IpfsDownloadError(
                        f"unexpected HTTP {status} while downloading {cid}"
                    )
                total = _response_total(response, downloaded)
                if progress is not None:
                    progress(DownloadProgress(cid, downloaded, total, False))
                with partial.open(mode) as output:
                    while chunk := response.read(self.chunk_size):
                        output.write(chunk)
                        downloaded += len(chunk)
                        if progress is not None:
                            progress(DownloadProgress(cid, downloaded, total, False))
                if total is None:
                    raise IpfsDownloadError(
                        f"gateway did not report content length for {cid}"
                    )
                if downloaded != total:
                    raise IpfsDownloadError(
                        f"incomplete download for {cid}: {downloaded} of {total} bytes"
                    )
        except (HTTPError, URLError, TimeoutError) as error:
            raise IpfsDownloadError(f"failed to download {cid}") from error


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _completion_marker_matches(path: Path, marker: Path) -> bool:
    if not marker.exists():
        return False
    try:
        value = marker.read_text(encoding="ascii")
        if value.startswith("{"):
            return int(json.loads(value)["size"]) == path.stat().st_size
        return int(value) == path.stat().st_size
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _write_completion_marker(
    path: Path,
    marker: Path,
    sha256: str | None = None,
) -> None:
    digest = _sha256_file(path) if sha256 is None else sha256
    marker.write_text(
        json.dumps(
            {"size": path.stat().st_size, "sha256": digest},
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="ascii",
    )


def _single_block_cid_matches(path: Path, cid: str) -> bool:
    if path.stat().st_size > _UNIXFS_BLOCK_SIZE:
        return False
    return single_block_file_cid_v0(path.read_bytes()) == cid


def _response_total(response: object, offset: int) -> int | None:
    headers = getattr(response, "headers")
    content_range = headers.get("Content-Range")
    if content_range and "/" in content_range:
        total = content_range.rsplit("/", 1)[1]
        if total != "*":
            return int(total)
    content_length = headers.get("Content-Length")
    return offset + int(content_length) if content_length is not None else None


def print_download_progress(progress: DownloadProgress) -> None:
    """Simple progress callback suitable for notebooks and Python sessions."""

    previous_bytes, previous_time = _DISPLAY_STATE.get(progress.cid, (-1, 0.0))
    now = time.monotonic()
    if (
        not progress.complete
        and previous_bytes >= 0
        and progress.downloaded - previous_bytes < 10 * 1024 * 1024
        and now - previous_time < 1.0
    ):
        return
    _DISPLAY_STATE[progress.cid] = (progress.downloaded, now)
    downloaded_mib = progress.downloaded / (1024 * 1024)
    if progress.total:
        total_mib = progress.total / (1024 * 1024)
        percentage = 100 * progress.downloaded / progress.total
        message = (
            f"{progress.cid}: {downloaded_mib:,.1f}/{total_mib:,.1f} MiB "
            f"({percentage:5.1f}%)"
        )
    else:
        message = f"{progress.cid}: {downloaded_mib:,.1f} MiB"
    end = "\n" if progress.complete else "\r"
    print(message, end=end, file=sys.stdout, flush=True)
    if progress.complete:
        _DISPLAY_STATE.pop(progress.cid, None)
