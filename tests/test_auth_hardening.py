# Copyright 2026 Aaron John Schlosser, PhD.
"""Session cookie setting and failed-login throttling.

Why: repeated password guesses should be slowed by a fixed lockout, without revealing which usernames
exist, and the Secure cookie flag must be configurable for HTTPS deployments.
How: drives AuthStore against a temporary SQLite database (with cheap password hashing) and a
tiny compiled copy of the login route, so no web server is started.
"""

from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import auth, config


def configure_auth(monkeypatch, tmp_path: Path, *, failures: int = 3, seconds: int = 300):
    """Point auth at a temp database with low PBKDF2 cost and the given failure limit and lockout time."""
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
    """Read one username's failure counter row directly from SQLite."""
    with store._connect() as conn:
        return conn.execute(
            "SELECT failures,locked_until FROM login_failures WHERE username_key=?",
            (username.strip().casefold(),),
        ).fetchone()


def test_session_cookie_secure_boolean_setting_is_environment_driven(monkeypatch):
    """SESSION_COOKIE_SECURE accepts true/false-style words and ignores garbage."""
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    assert config._bool_env("SESSION_COOKIE_SECURE", False) is True
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "off")
    assert config._bool_env("SESSION_COOKIE_SECURE", True) is False
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "not-a-bool")
    assert config._bool_env("SESSION_COOKIE_SECURE", False) is False


def test_failed_login_lockout_persists_expires_and_success_resets(monkeypatch, tmp_path: Path):
    """Failures lock after the limit, persist across store instances, expire, and reset on success.

    Two failures then a success clears the counter. Three failures lock the name (also for a second
    store object using the same database); once the lock time passes the correct password works again.
    """
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

    expired = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with second._connect() as conn:
        conn.execute(
            "UPDATE login_failures SET locked_until=? WHERE username_key=?",
            (expired, "scholar"),
        )
    restored = second.authenticate("Scholar", "correct-horse")
    assert restored is not None and restored.id == user.id
    assert throttle_row(second, "scholar") is None


def test_unknown_user_is_throttled_without_requiring_an_account(monkeypatch, tmp_path: Path):
    """Nonexistent usernames are throttled exactly like real ones.

    Why: a different behavior would reveal which accounts exist.
    """
    configure_auth(monkeypatch, tmp_path, failures=2)
    store = auth.AuthStore()
    assert store.authenticate("does-not-exist", "guess-1") is None
    assert store.authenticate("does-not-exist", "guess-2") is None
    row = throttle_row(store, "does-not-exist")
    assert row is not None
    assert int(row["failures"]) == 2
    assert row["locked_until"]


def test_concurrent_failures_across_store_instances_cannot_bypass_lockout(monkeypatch, tmp_path: Path):
    """Eight parallel wrong guesses across four store objects still lock at exactly 4 failures.

    The counter update is serialized in the database, so concurrency cannot smuggle extra attempts.
    """
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


def test_password_reset_revokes_sessions_and_clears_login_lockout(monkeypatch, tmp_path: Path):
    """A reset password takes effect for existing sessions and clears stale throttles."""
    import pytest

    configure_auth(monkeypatch, tmp_path, failures=2)
    store = auth.AuthStore()
    user = store.create_user("Scholar", "old-password", "researcher")
    token = store.create_session(user.id)
    assert store.user_for_session(token) is not None
    assert store.authenticate("Scholar", "wrong-password") is None
    assert throttle_row(store, "Scholar") is not None
    verified_login = store.authenticate("Scholar", "old-password")
    assert verified_login is not None

    store.update_user(user.id, password="new-password")

    assert store.user_for_session(token) is None
    assert throttle_row(store, "Scholar") is None
    with pytest.raises(ValueError, match="Account changed during sign-in"):
        store.create_session(user.id, expected_updated_at=verified_login.updated_at)
    assert store.authenticate("Scholar", "old-password") is None
    assert store.authenticate("Scholar", "new-password") is not None


def test_concurrent_bootstrap_creates_exactly_one_initial_administrator(monkeypatch, tmp_path: Path):
    """Separate app workers cannot both pass the first-account check."""
    configure_auth(monkeypatch, tmp_path)
    stores = [auth.AuthStore(), auth.AuthStore()]
    barrier = threading.Barrier(2)

    def bootstrap(index: int) -> bool:
        barrier.wait()
        try:
            stores[index].bootstrap_admin(f"owner-{index}", "secret-password")
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(bootstrap, range(2)))

    assert sorted(outcomes) == [False, True]
    assert len(stores[0].list_users()) == 1
    assert stores[0].list_users()[0].role == "admin"


def test_concurrent_admin_updates_preserve_one_active_administrator(monkeypatch, tmp_path: Path):
    """The last-admin guard is serialized across independent AuthStore instances."""
    configure_auth(monkeypatch, tmp_path)
    stores = [auth.AuthStore(), auth.AuthStore()]
    admins = [stores[0].bootstrap_admin("owner-one", "secret-password")]
    admins.append(stores[0].create_user("owner-two", "secret-password", "admin"))
    barrier = threading.Barrier(2)

    def deactivate(index: int) -> bool:
        barrier.wait()
        try:
            stores[index].update_user(admins[index].id, active=False)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(deactivate, range(2)))

    assert sorted(outcomes) == [False, True]
    active_admins = [user for user in stores[0].list_users() if user.role == "admin" and user.active]
    assert len(active_admins) == 1


def test_concurrent_admin_delete_and_deactivation_preserve_one_active_administrator(
    monkeypatch, tmp_path: Path
):
    """Delete and deactivate operations share the same serialized last-admin invariant."""
    configure_auth(monkeypatch, tmp_path)
    stores = [auth.AuthStore(), auth.AuthStore()]
    first = stores[0].bootstrap_admin("owner-one", "secret-password")
    second = stores[0].create_user("owner-two", "secret-password", "admin")
    barrier = threading.Barrier(2)

    def delete_first() -> bool:
        barrier.wait()
        try:
            stores[0].delete_user(first.id)
            return True
        except ValueError:
            return False

    def deactivate_second() -> bool:
        barrier.wait()
        try:
            stores[1].update_user(second.id, active=False)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(delete_first), pool.submit(deactivate_second)]
        outcomes = [result.result() for result in results]

    assert sorted(outcomes) == [False, True]
    active_admins = [user for user in stores[0].list_users() if user.role == "admin" and user.active]
    assert len(active_admins) == 1


def test_lockout_remaining_is_reported_identically_for_real_and_unknown_usernames(monkeypatch, tmp_path: Path):
    """The remaining lock time is 0 before locking, about the lock length after, and 0 once expired.

    Real and unknown usernames must behave the same.
    """
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
        conn.execute("UPDATE login_failures SET locked_until=?", ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(),))
    assert store.login_lockout_remaining("Scholar") == 0


def _login_route(store):
    """Compile only the login route so importing application service singletons is unnecessary."""
    import ast

    from fastapi import HTTPException

    path = ROOT / "api/app/routers/auth.py"
    node = next(n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef) and n.name == "auth_login")
    node.decorator_list = []
    scope = {
        "auth_store": store, "HTTPException": HTTPException,
        "_session_cookie": lambda response, token: None,
        "AuthLoginRequest": object, "Response": object,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec",
                 flags=__import__("__future__").annotations.compiler_flag), scope)
    return scope["auth_login"], HTTPException


def test_login_route_returns_429_with_retry_after_for_locked_usernames(monkeypatch, tmp_path: Path):
    """The third attempt gets HTTP 429 with Retry-After, for real and unknown names alike.

    Attempts 1-2 return 401. Attempt 3 returns 429 with a login_locked code and a retry time that
    matches the header. Even the correct password is refused with 429 while locked.
    """
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


def test_user_select_rejects_unknown_sql_fragments():
    """User listing SQL only interpolates a closed set of WHERE/ORDER fragments."""
    store = auth.AuthStore.__new__(auth.AuthStore)
    assert "WHERE u.id=?" in store._user_select("WHERE u.id=?")
    try:
        store._user_select("WHERE u.role='admin'")
        raise AssertionError("unknown WHERE clause must be rejected")
    except ValueError as exc:
        assert "Unsupported user query clause" in str(exc)
    try:
        store._user_select(order="ORDER BY u.password_hash")
        raise AssertionError("unknown ORDER clause must be rejected")
    except ValueError as exc:
        assert "Unsupported user query clause" in str(exc)
