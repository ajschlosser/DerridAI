# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import auth, config


def configure_auth(monkeypatch, tmp_path: Path, *, failures: int = 3, seconds: int = 300):
    monkeypatch.setattr(auth, "PBKDF2_ITERATIONS", 1_000)
    monkeypatch.setattr(
        auth,
        "settings",
        SimpleNamespace(
            auth_db_path=str(tmp_path / "auth.sqlite3"),
            auth_login_max_failures=failures,
            auth_login_lockout_seconds=seconds,
        ),
    )


def throttle_row(store: auth.AuthStore, username: str):
    with store._connect() as conn:
        return conn.execute(
            "SELECT failures,locked_until FROM login_failures WHERE username_key=?",
            (username.strip().casefold(),),
        ).fetchone()


def test_session_cookie_secure_boolean_setting_is_environment_driven(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    assert config._bool_env("SESSION_COOKIE_SECURE", False) is True
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "off")
    assert config._bool_env("SESSION_COOKIE_SECURE", True) is False
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "not-a-bool")
    assert config._bool_env("SESSION_COOKIE_SECURE", False) is False


def test_failed_login_lockout_persists_expires_and_success_resets(monkeypatch, tmp_path: Path):
    configure_auth(monkeypatch, tmp_path, failures=3, seconds=300)
    first = auth.AuthStore()
    user = first.create_user("Scholar", "correct-horse", "researcher")

    assert first.authenticate("Scholar", "wrong-1") is None
    assert first.authenticate("scholar", "wrong-2") is None
    assert first.authenticate("SCHOLAR", "correct-horse").id == user.id
    assert throttle_row(first, "scholar") is None

    assert first.authenticate("Scholar", "wrong-1") is None
    assert first.authenticate("Scholar", "wrong-2") is None
    assert first.authenticate("Scholar", "wrong-3") is None
    locked = throttle_row(first, "scholar")
    assert locked is not None
    assert int(locked["failures"]) == 3
    assert locked["locked_until"]

    second = auth.AuthStore()
    assert second.authenticate("Scholar", "correct-horse") is None

    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with second._connect() as conn:
        conn.execute(
            "UPDATE login_failures SET locked_until=? WHERE username_key=?",
            (expired, "scholar"),
        )
    restored = second.authenticate("Scholar", "correct-horse")
    assert restored is not None and restored.id == user.id
    assert throttle_row(second, "scholar") is None


def test_unknown_user_is_throttled_without_requiring_an_account(monkeypatch, tmp_path: Path):
    configure_auth(monkeypatch, tmp_path, failures=2)
    store = auth.AuthStore()
    assert store.authenticate("does-not-exist", "guess-1") is None
    assert store.authenticate("does-not-exist", "guess-2") is None
    row = throttle_row(store, "does-not-exist")
    assert row is not None
    assert int(row["failures"]) == 2
    assert row["locked_until"]


def test_concurrent_failures_across_store_instances_cannot_bypass_lockout(monkeypatch, tmp_path: Path):
    configure_auth(monkeypatch, tmp_path, failures=4)
    creator = auth.AuthStore()
    creator.create_user("Concurrent", "correct-horse", "researcher")
    stores = [auth.AuthStore() for _ in range(4)]

    def fail(index: int):
        return stores[index % len(stores)].authenticate("Concurrent", f"wrong-{index}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(result is None for result in pool.map(fail, range(8)))

    row = throttle_row(creator, "concurrent")
    assert row is not None
    assert int(row["failures"]) == 4
    assert row["locked_until"]
    assert stores[0].authenticate("Concurrent", "correct-horse") is None
