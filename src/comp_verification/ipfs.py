"""Resumable IPFS gateway downloads into the ignored local cache."""

from __future__ import annotations

import hashlib
from http.client import HTTPException
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .encoding import file_cid_v0, single_block_file_cid_v0


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
        gateway_token: str | None = None,
        timeout: float = 120,
        attempts: int = 5,
        retry_base_delay: float = 2.0,
        chunk_size: int = 1024 * 1024,
        range_request_bytes: int = 16 * 1024 * 1024,
        max_concurrent_ranges_per_download: int = 4,
        max_concurrent_downloads: int = 8,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache = cache
        self.user_agent = user_agent
        self.gateway_token = gateway_token
        self.timeout = timeout
        self.attempts = attempts
        self.retry_base_delay = retry_base_delay
        self.chunk_size = chunk_size
        self.range_request_bytes = range_request_bytes
        self.max_concurrent_ranges_per_download = max_concurrent_ranges_per_download
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
                    if self.max_concurrent_ranges_per_download == 1:
                        self._download_to_partial(cid, partial, progress)
                    else:
                        self._download_to_partial_concurrently(
                            cid, partial, progress
                        )
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
        head_request = Request(
            self._artifact_url(cid),
            headers=self._request_headers(),
            method="HEAD",
        )
        try:
            with urlopen(head_request, timeout=self.timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    return int(content_length)
        except (HTTPError, URLError, TimeoutError, ValueError):
            pass

        request = Request(
            self._artifact_url(cid),
            headers=self._request_headers(range_value="bytes=0-0"),
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

    def download_many_best_effort(
        self,
        cids: list[str] | set[str],
        *,
        progress: ProgressCallback | None = None,
    ) -> tuple[list[DownloadedArtifact], dict[str, str]]:
        """Download concurrently while retaining per-CID failures as evidence."""

        ordered = sorted(set(cids))
        artifacts: list[DownloadedArtifact] = []
        failures: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            futures = {
                executor.submit(self.download, cid, progress=progress): cid
                for cid in ordered
            }
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    artifacts.append(future.result())
                except IpfsDownloadError as error:
                    failures[cid] = str(error)
        artifacts.sort(key=lambda artifact: artifact.cid)
        return artifacts, dict(sorted(failures.items()))

    def prune_verified_artifact(self, artifact: DownloadedArtifact) -> None:
        """Delete exactly one cache artifact and marker after strict hash checks."""

        destination = self.cache / artifact.cid
        marker = destination.parent / f"{destination.name}.complete"
        if artifact.path != destination:
            raise ValueError("artifact path is outside the expected IPFS cache location")
        if destination.is_symlink() or marker.is_symlink():
            raise ValueError("refusing to prune symlinked IPFS cache evidence")
        if not destination.is_file() or not marker.is_file():
            raise FileNotFoundError("verified artifact or completion marker is missing")
        if destination.stat().st_size != artifact.size:
            raise IpfsDownloadError("cached artifact size changed before pruning")
        if _sha256_file(destination) != artifact.sha256:
            raise IpfsDownloadError("cached artifact hash changed before pruning")
        if file_cid_v0(destination) != artifact.cid:
            raise IpfsDownloadError("cached artifact CID changed before pruning")
        try:
            marker_text = marker.read_text(encoding="ascii")
            if marker_text.startswith("{"):
                marker_evidence = json.loads(marker_text)
                if marker_evidence != {
                    "sha256": artifact.sha256,
                    "size": artifact.size,
                }:
                    raise IpfsDownloadError(
                        "completion marker differs from verified artifact"
                    )
            elif int(marker_text) != artifact.size:
                raise IpfsDownloadError(
                    "legacy completion marker differs from verified artifact"
                )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise IpfsDownloadError("completion marker is not verifiable") from error
        # Remove the marker first: interruption can leave recoverable raw bytes, but
        # can never leave a marker claiming that missing bytes are complete.
        marker.unlink()
        destination.unlink()

    def _download_to_partial(
        self,
        cid: str,
        partial: Path,
        progress: ProgressCallback | None,
    ) -> None:
        while True:
            offset = partial.stat().st_size if partial.exists() else 0
            # Some historical Pinata objects advertise a zero-length HEAD and
            # never answer Range, while an ordinary GET returns the full object.
            # Detect that known anomaly before spending a full socket timeout on
            # the doomed Range request. Existing partials always remain resumable.
            if offset == 0:
                try:
                    advertised_size = self._remote_size(cid)
                except IpfsDownloadError:
                    advertised_size = None
                if advertised_size == 0:
                    self._download_without_range(cid, partial, progress)
                    return
            range_end = offset + self.range_request_bytes - 1
            request = Request(
                self._artifact_url(cid),
                headers=self._request_headers(
                    range_value=f"bytes={offset}-{range_end}"
                ),
            )
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    status = getattr(response, "status", 200)
                    if status == 206:
                        mode = "ab" if offset else "wb"
                        downloaded = offset
                    elif status == 200:
                        # A gateway may ignore Range. Restart from its complete
                        # response rather than appending duplicate bytes.
                        mode = "wb"
                        downloaded = 0
                    else:
                        raise IpfsDownloadError(
                            f"unexpected HTTP {status} while downloading {cid}"
                        )
                    total = _response_total(response, downloaded)
                    if progress is not None:
                        progress(DownloadProgress(cid, downloaded, total, False))
                    segment_start = downloaded
                    with partial.open(mode) as output:
                        while chunk := response.read(self.chunk_size):
                            output.write(chunk)
                            downloaded += len(chunk)
                            if progress is not None:
                                progress(
                                    DownloadProgress(cid, downloaded, total, False)
                                )
                    if total is None:
                        raise IpfsDownloadError(
                            f"gateway did not report content length for {cid}"
                        )
                    if downloaded == total:
                        return
                    if downloaded > total or downloaded == segment_start:
                        raise IpfsDownloadError(
                            f"invalid ranged download for {cid}: "
                            f"{downloaded} of {total} bytes"
                        )
            except (HTTPError, URLError, TimeoutError) as error:
                # Some Pinata gateway cache entries serve the complete object to
                # an ordinary GET but advertise Content-Length: 0 to HEAD and
                # never answer Range. This has been observed for small historical
                # submission archives. Only use the non-range fallback for that
                # exact zero-length signal, and only before any partial bytes have
                # been retained, so large resumable downloads are never restarted.
                if offset == 0:
                    try:
                        advertised_size = self._remote_size(cid)
                    except IpfsDownloadError:
                        advertised_size = None
                    if advertised_size == 0:
                        self._download_without_range(cid, partial, progress)
                        return
                raise IpfsDownloadError(f"failed to download {cid}") from error

    def _download_without_range(
        self,
        cid: str,
        partial: Path,
        progress: ProgressCallback | None,
    ) -> None:
        """Stream one complete response for a gateway's zero-length HEAD bug."""

        request = Request(
            self._artifact_url(cid),
            headers=self._request_headers(),
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise IpfsDownloadError(
                        f"unexpected HTTP {status} while downloading {cid}"
                    )
                content_length = response.headers.get("Content-Length")
                total = int(content_length) if content_length is not None else None
                downloaded = 0
                if progress is not None:
                    progress(DownloadProgress(cid, downloaded, total, False))
                with partial.open("wb") as output:
                    while chunk := response.read(self.chunk_size):
                        output.write(chunk)
                        downloaded += len(chunk)
                        if progress is not None:
                            progress(DownloadProgress(cid, downloaded, total, False))
                if downloaded == 0:
                    raise IpfsDownloadError(
                        f"gateway returned an empty plain response for {cid}"
                    )
                if total is not None and downloaded != total:
                    raise IpfsDownloadError(
                        f"short plain response for {cid}: {downloaded} of {total}"
                    )
        except (HTTPError, URLError, TimeoutError) as error:
            raise IpfsDownloadError(f"failed plain download for {cid}") from error

    def _download_to_partial_concurrently(
        self,
        cid: str,
        partial: Path,
        progress: ProgressCallback | None,
    ) -> None:
        """Fetch persistent byte ranges concurrently, then assemble in order."""

        total = self._remote_size(cid)
        prefix_size = partial.stat().st_size if partial.exists() else 0
        if prefix_size > total:
            raise IpfsDownloadError(
                f"partial file for {cid} is larger than gateway content"
            )
        if prefix_size == total:
            return

        range_root = self.cache / ".ranges" / cid
        range_root.mkdir(parents=True, exist_ok=True)
        ranges = [
            (start, min(start + self.range_request_bytes - 1, total - 1))
            for start in range(prefix_size, total, self.range_request_bytes)
        ]
        received: dict[tuple[int, int], int] = {}
        lock = threading.Lock()
        for start, end in ranges:
            path = range_root / f"{start}-{end}.part"
            size = path.stat().st_size if path.exists() else 0
            expected = end - start + 1
            if size > expected:
                raise IpfsDownloadError(f"oversized retained range for {cid}")
            received[(start, end)] = size

        def report_range(key: tuple[int, int], size: int) -> None:
            with lock:
                received[key] = size
                downloaded = prefix_size + sum(received.values())
            if progress is not None:
                progress(DownloadProgress(cid, downloaded, total, False))

        if progress is not None:
            report_range((-1, -1), 0)
            received.pop((-1, -1), None)

        errors: list[IpfsDownloadError] = []
        with ThreadPoolExecutor(
            max_workers=self.max_concurrent_ranges_per_download
        ) as executor:
            futures = {
                executor.submit(
                    self._download_range_segment,
                    cid,
                    start,
                    end,
                    range_root / f"{start}-{end}.part",
                    report_range,
                ): (start, end)
                for start, end in ranges
                if received[(start, end)] < end - start + 1
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except IpfsDownloadError as error:
                    errors.append(error)
        if errors:
            raise errors[0]

        with partial.open("ab") as output:
            for start, end in ranges:
                path = range_root / f"{start}-{end}.part"
                expected = end - start + 1
                if not path.is_file() or path.stat().st_size != expected:
                    raise IpfsDownloadError(f"incomplete retained range for {cid}")
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(self.chunk_size), b""):
                        output.write(chunk)
                path.unlink()
        range_root.rmdir()
        ranges_parent = range_root.parent
        if not any(ranges_parent.iterdir()):
            ranges_parent.rmdir()

    def _download_range_segment(
        self,
        cid: str,
        start: int,
        end: int,
        destination: Path,
        report: Callable[[tuple[int, int], int], None],
    ) -> None:
        key = (start, end)
        existing = destination.stat().st_size if destination.exists() else 0
        expected = end - start + 1
        if existing == expected:
            report(key, existing)
            return
        request_start = start + existing
        request = Request(
            self._artifact_url(cid),
            headers=self._request_headers(
                range_value=f"bytes={request_start}-{end}"
            ),
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                content_range = response.headers.get("Content-Range")
                expected_prefix = f"bytes {request_start}-{end}/"
                if status != 206 or not content_range.startswith(expected_prefix):
                    raise IpfsDownloadError(
                        f"gateway returned an invalid range for {cid}: "
                        f"{status} {content_range!r}"
                    )
                with destination.open("ab") as output:
                    while chunk := response.read(self.chunk_size):
                        output.write(chunk)
                        existing += len(chunk)
                        report(key, existing)
        except (HTTPError, URLError, TimeoutError, OSError, HTTPException) as error:
            raise IpfsDownloadError(
                f"failed range {request_start}-{end} for {cid}"
            ) from error
        if existing != expected:
            raise IpfsDownloadError(
                f"short range {start}-{end} for {cid}: {existing} of {expected}"
            )

    def _request_headers(self, *, range_value: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/octet-stream",
            "User-Agent": self.user_agent,
        }
        if range_value is not None:
            headers["Range"] = range_value
        return headers

    def _artifact_url(self, cid: str) -> str:
        url = f"{self.base_url}/{cid}"
        if self.gateway_token:
            url += "?" + urlencode({"pinataGatewayToken": self.gateway_token})
        return url


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
