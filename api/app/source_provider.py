# Copyright 2026 Aaron John Schlosser, PhD.
"""Provider contract and the one bounded HTTP boundary every source provider uses.

Transport lives here, parsing lives in each provider module, and global
reconciliation lives in ``source_reconcile``. Tests inject an ``httpx``
transport instead of patching calls scattered through orchestration code.
"""
from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from .source_identity import (
    CaptureError,
    CaptureErrorCode,
    CaptureOptions,
    ResolvedAuthor,
    SourceCandidate,
)

# Wikimedia asks API clients to identify the tool and a way to reach its maintainers.
USER_AGENT = "DerridAI/1.0 (https://github.com/ajschlosser/DerridAI; local scholarly research tool)"


@dataclass(frozen=True)
class ProviderPolicy:
    """Central rate/concurrency/retry policy for one provider family. Adjust here, nowhere else."""

    hosts: tuple[str, ...]  # exact hosts or ".suffix" entries
    min_interval_s: float
    max_concurrent: int
    max_attempts: int = 3
    backoff_s: float = 1.0
    timeout_s: float = 45.0
    max_response_bytes: int = 16 * 1024 * 1024


POLICIES: dict[str, ProviderPolicy] = {
    "gutenberg": ProviderPolicy(
        hosts=("www.gutenberg.org", "gutenberg.org", "gutendex.com"), min_interval_s=1.0, max_concurrent=1
    ),
    # One Wikimedia gate covers Wikidata, Meta and every Wikisource project.
    "wikimedia": ProviderPolicy(
        hosts=(".wikisource.org", "wikisource.org", "www.wikidata.org", "meta.wikimedia.org"),
        min_interval_s=0.2,
        max_concurrent=2,
    ),
}


def host_allowed(url: str, policy: ProviderPolicy) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    if parsed.port not in (None, 443):
        return False
    return any(host == entry or (entry.startswith(".") and host.endswith(entry)) for entry in policy.hosts)


class _Gate:
    def __init__(self, policy: ProviderPolicy) -> None:
        self.policy = policy
        self.semaphore = threading.BoundedSemaphore(policy.max_concurrent)
        self.lock = threading.Lock()
        self.last = 0.0

    def wait_turn(self) -> None:
        with self.lock:
            delay = self.policy.min_interval_s - (time.monotonic() - self.last)
            if delay > 0:
                time.sleep(delay)
            self.last = time.monotonic()


_GATES: dict[str, _Gate] = {name: _Gate(policy) for name, policy in POLICIES.items()}


class ProviderHttp:
    """Allow-listed, rate-limited, bounded, cancellable HTTP for one provider family.

    Redirects are never followed implicitly: a remote API naming a URL is not
    permission to fetch an arbitrary host (SSRF). Callers that accept a
    redirect re-validate its target with :func:`host_allowed`.
    """

    def __init__(
        self,
        family: str,
        *,
        client: httpx.Client | None = None,
        cancelled: Callable[[], bool] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.policy = POLICIES[family]
        self._gate = _GATES[family]
        self._client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(self.policy.timeout_s, connect=10.0),
            follow_redirects=False,
        )
        self._cancelled = cancelled or (lambda: False)
        self._sleep = sleep

    def check_cancelled(self) -> None:
        if self._cancelled():
            raise CaptureError(CaptureErrorCode.CANCELLED, "The capture was cancelled.")

    def _request(self, url: str, params: dict[str, Any] | None, *, max_bytes: int) -> httpx.Response:
        if not host_allowed(url, self.policy):
            raise CaptureError(CaptureErrorCode.UNSUPPORTED_SOURCE, "The provider URL is not on an allowed host.", detail=url)
        last: CaptureError | None = None
        for attempt in range(self.policy.max_attempts):
            self.check_cancelled()
            try:
                with self._gate.semaphore:
                    self._gate.wait_turn()
                    with self._client.stream("GET", url, params=params, headers={"User-Agent": USER_AGENT}) as response:
                        if response.status_code == 429 or response.status_code >= 500:
                            code = CaptureErrorCode.RATE_LIMITED if response.status_code == 429 else CaptureErrorCode.PROVIDER_UNAVAILABLE
                            raise CaptureError(code, f"The provider answered HTTP {response.status_code}.")
                        chunks: list[bytes] = []
                        total = 0
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > max_bytes:
                                raise CaptureError(CaptureErrorCode.SOURCE_TOO_LARGE, "The provider response exceeds the size limit.")
                            chunks.append(chunk)
                        # Re-materialize a plain response so callers can read it after the stream closes.
                        # iter_bytes already decoded any Content-Encoding, so drop it (and the stale length).
                        headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}}
                        return httpx.Response(response.status_code, headers=headers, content=b"".join(chunks), request=response.request)
            except CaptureError as exc:
                if not exc.transient:
                    raise
                last = exc
            except httpx.TimeoutException as exc:
                last = CaptureError(CaptureErrorCode.NETWORK_TIMEOUT, "The provider did not answer in time.", detail=str(exc))
            except httpx.TransportError as exc:
                last = CaptureError(CaptureErrorCode.PROVIDER_UNAVAILABLE, "Could not reach the provider.", detail=str(exc))
            if attempt + 1 < self.policy.max_attempts:
                # Bounded exponential backoff, cancellable between attempts.
                self.check_cancelled()
                self._sleep(self.policy.backoff_s * (2**attempt))
        assert last is not None
        raise last

    def get(self, url: str, params: dict[str, Any] | None = None, *, max_bytes: int | None = None) -> httpx.Response:
        return self._request(url, params, max_bytes=max_bytes or self.policy.max_response_bytes)

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.get(url, params)
        if response.status_code == 404:
            raise CaptureError(CaptureErrorCode.SOURCE_NOT_FOUND, "The provider has no such item.", detail=url)
        if response.status_code >= 400:
            raise CaptureError(CaptureErrorCode.INVALID_PROVIDER_RESPONSE, f"The provider answered HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise CaptureError(CaptureErrorCode.INVALID_PROVIDER_RESPONSE, "The provider returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise CaptureError(CaptureErrorCode.INVALID_PROVIDER_RESPONSE, "The provider returned an unexpected payload.")
        error = payload.get("error")
        if isinstance(error, dict):
            code = str(error.get("code") or "")
            if code in {"ratelimited", "maxlag"}:
                raise CaptureError(CaptureErrorCode.RATE_LIMITED, "The provider asked DerridAI to slow down.")
            if code in {"missingtitle", "nosuchpageid", "no-such-entity"}:
                raise CaptureError(CaptureErrorCode.SOURCE_NOT_FOUND, "The provider has no such page.", detail=str(error.get("info") or ""))
            raise CaptureError(CaptureErrorCode.INVALID_PROVIDER_RESPONSE, "The provider reported an error.", detail=str(error.get("info") or code))
        return payload


def charset_of(content_type: str, default: str = "utf-8") -> str:
    match = re.search(r"charset=([^; ]+)", content_type or "", re.I)
    return match.group(1).strip('"') if match else default


@dataclass
class AcquiredSource:
    """Verified bytes plus the provider provenance that travels into SourceDocument registration."""

    data: bytes
    filename: str
    content_type: str
    source_uri: str
    catalog_metadata: dict[str, Any]


@dataclass
class DiscoveryReport:
    """What one provider searched, so a capture can state its coverage truthfully."""

    provider: str
    projects_searched: list[str]
    identities_used: list[str]
    result_count: int = 0
    pagination_complete: bool = True
    catalog_version: str | None = None
    catalog_refreshed_at: str | None = None
    endpoint: str | None = None
    warnings: list[str] | None = None
    errors: list[dict[str, str]] | None = None


ProgressCallback = Callable[[str, dict[str, Any]], None]


class SourceProvider(Protocol):
    """A digital library that can enumerate and fetch representations for a resolved person."""

    provider_id: str

    def enumerate_author_sources(
        self, author: ResolvedAuthor, options: CaptureOptions, report: DiscoveryReport, progress: ProgressCallback
    ) -> Iterator[SourceCandidate]: ...

    def fetch_source(self, candidate: SourceCandidate, *, max_bytes: int) -> AcquiredSource: ...
