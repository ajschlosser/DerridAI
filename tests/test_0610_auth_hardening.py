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


def test_lockout_remaining_is_reported_identically_for_real_and_unknown_usernames(monkeypatch, tmp_path: Path):
    configure_auth(monkeypatch, tmp_path, failures=2, seconds=120)
    store = auth.AuthStore()
    store.create_user("Scholar", "correct-horse", "researcher")

    assert store.login_lockout_remaining("Scholar") == 0
    assert store.login_lockout_remaining("ghost") == 0
    for name in ("Scholar", "ghost"):
        store.authenticate(name, "wrong-1")
        assert store.login_lockout_remaining(name) == 0
        store.authenticate(name, "wrong-2")

    real, ghost = store.login_lockout_remaining("scholar"), store.login_lockout_remaining("GHOST")
    assert 100 < real <= 121 and 100 < ghost <= 121

    with store._connect() as conn:
        conn.execute("UPDATE login_failures SET locked_until=?", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),))
    assert store.login_lockout_remaining("Scholar") == 0


def _login_route(store):
    """Compile only the login route so importing main.py's global workers is unnecessary."""
    import ast
    from fastapi import HTTPException

    path = ROOT / "api/app/main.py"
    node = next(n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef) and n.name == "auth_login")
    node.decorator_list = []
    scope = {
        "auth_store": store, "HTTPException": HTTPException,
        "_session_cookie": lambda response, token: None,
        "AuthLoginRequest": object, "Response": object,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), scope)
    return scope["auth_login"], HTTPException


def test_login_route_returns_429_with_retry_after_for_locked_usernames(monkeypatch, tmp_path: Path):
    configure_auth(monkeypatch, tmp_path, failures=2, seconds=120)
    store = auth.AuthStore()
    store.create_user("Scholar", "correct-horse", "researcher")
    login, HTTPException = _login_route(store)
    body = lambda name, password: SimpleNamespace(username=name, password=password)  # noqa: E731

    statuses = {}
    for name in ("Scholar", "ghost"):
        seen = []
        for _ in range(3):
            try:
                login(body(name, "wrong"), None)
            except HTTPException as exc:
                seen.append(exc)
        statuses[name] = seen
        assert [exc.status_code for exc in seen] == [401, 401, 429]
        locked = seen[-1]
        assert locked.detail["code"] == "login_locked"
        assert 100 < locked.detail["retry_after_seconds"] <= 121
        assert locked.headers["Retry-After"] == str(locked.detail["retry_after_seconds"])

    # The correct password is refused while locked, with the same 429.
    try:
        login(body("Scholar", "correct-horse"), None)
        raise AssertionError("locked account must not sign in")
    except HTTPException as exc:
        assert exc.status_code == 429
