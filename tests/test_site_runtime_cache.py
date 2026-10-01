# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from app import site_runtime_cache as cache


def _artifact(role: str, filename: str, payload: bytes) -> dict:
    return {
        "role": role,
        "filename": filename,
        "url": f"https://cdn.example.test/{filename}",
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


_PAYLOADS = {"engine": b"engine-bytes", "license": b"license", "wasm_factory": b"factory", "wasm": b"\x00asm-binary"}


class _Response(io.BytesIO):
    def __init__(self, payload: bytes, url: str) -> None:
        super().__init__(payload)
        self._url = url

    def geturl(self) -> str:
        return self._url

    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class _Opener:
    def __init__(self, overrides: dict[str, bytes] | None = None, redirect: str | None = None) -> None:
        self.requested: list[str] = []
        self.overrides = overrides or {}
        self.redirect = redirect

    def __call__(self, url: str, timeout: int = 0) -> _Response:
        self.requested.append(url)
        name = url.rsplit("/", 1)[-1]
        role = next(item["role"] for item in cache.ARTIFACTS if item["filename"] == name)
        return _Response(self.overrides.get(name, _PAYLOADS[role]), self.redirect or url)


@pytest.fixture(autouse=True)
def _tiny_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        cache,
        "ARTIFACTS",
        (
            _artifact("engine", "transformers.min.js", _PAYLOADS["engine"]),
            _artifact("license", "LICENSE-transformers.js.txt", _PAYLOADS["license"]),
            _artifact("wasm_factory", "ort-wasm-simd-threaded.mjs", _PAYLOADS["wasm_factory"]),
            _artifact("wasm", "ort-wasm-simd-threaded.wasm", _PAYLOADS["wasm"]),
        ),
    )
    monkeypatch.setattr(cache, "runtime_dir", lambda: tmp_path / "site_runtime" / "transformers")


def test_first_use_downloads_and_verifies_then_later_exports_use_the_cache() -> None:
    assert cache.is_cached() is False
    first = _Opener()
    files = cache.ensure_runtime(first)
    assert files == _PAYLOADS
    assert len(first.requested) == 4
    assert cache.is_cached() is True

    second = _Opener()
    assert cache.ensure_runtime(second) == _PAYLOADS
    assert second.requested == []


def test_a_corrupted_cached_file_is_downloaded_again() -> None:
    cache.ensure_runtime(_Opener())
    (cache.runtime_dir() / "ort-wasm-simd-threaded.mjs").write_bytes(b"tampered")
    repair = _Opener()
    assert cache.ensure_runtime(repair)["wasm_factory"] == _PAYLOADS["wasm_factory"]
    assert [url.rsplit("/", 1)[-1] for url in repair.requested] == ["ort-wasm-simd-threaded.mjs"]


def test_a_download_that_fails_verification_is_rejected_and_leaves_nothing() -> None:
    # Same length, different bytes: only the SHA-256 check can catch this.
    opener = _Opener({"transformers.min.js": b"X" * len(_PAYLOADS["engine"])})
    with pytest.raises(cache.RuntimeUnavailableError, match="SHA-256"):
        cache.ensure_runtime(opener)
    assert not (cache.runtime_dir() / "transformers.min.js").exists()
    assert not list(cache.runtime_dir().glob("*.part"))
    assert cache.is_cached() is False


def test_oversized_and_truncated_downloads_are_rejected() -> None:
    with pytest.raises(cache.RuntimeUnavailableError, match="larger than"):
        cache.ensure_runtime(_Opener({"transformers.min.js": _PAYLOADS["engine"] + b"extra"}))
    with pytest.raises(cache.RuntimeUnavailableError, match="expected"):
        cache.ensure_runtime(_Opener({"transformers.min.js": _PAYLOADS["engine"][:-1]}))


def test_redirects_to_plain_http_are_rejected() -> None:
    with pytest.raises(cache.RuntimeUnavailableError, match="non-HTTPS"):
        cache.ensure_runtime(_Opener(redirect="http://cdn.example.test/x"))


def test_network_failures_are_reported_as_unavailable_not_as_server_errors() -> None:
    def offline(_url: str, timeout: int = 0) -> _Response:
        raise OSError("network unreachable")

    with pytest.raises(cache.RuntimeUnavailableError, match="network unreachable"):
        cache.ensure_runtime(offline)


def test_download_progress_reports_bytes_and_delete_clears_the_cache() -> None:
    events: list[dict] = []
    cache.ensure_runtime(_Opener(), on_progress=events.append)
    assert events[-1]["status"] == "complete"
    assert any(event.get("status") == "progress" and event["received_total"] > 0 for event in events)
    assert cache.is_cached() is True
    cache.delete_runtime()
    assert cache.is_cached() is False


def test_info_and_notice_describe_the_pinned_sources_without_downloading() -> None:
    info = cache.runtime_info()
    assert info["cached"] is False
    assert info["version"] == cache.TRANSFORMERS_VERSION
    assert info["download_bytes"] == cache.DOWNLOAD_BYTES
    notice = cache.notice_text()
    for item in cache.ARTIFACTS:
        if item["role"] != "license":
            assert item["sha256"] in notice


def test_the_real_pinned_artifacts_are_https_and_complete() -> None:
    import importlib

    real = importlib.reload(cache)
    try:
        assert [item["role"] for item in real.ARTIFACTS] == ["engine", "license", "wasm_factory", "wasm"]
        assert all(item["url"].startswith("https://") for item in real.ARTIFACTS)
        assert all(len(item["sha256"]) == 64 and item["size"] > 0 for item in real.ARTIFACTS)
        assert real.DOWNLOAD_BYTES > 10_000_000
    finally:
        importlib.reload(cache)
