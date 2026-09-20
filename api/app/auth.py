# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import settings

type Role = str

_USER_SELECT_WHERES = frozenset(
    {
        "",
        "WHERE u.id=?",
        "WHERE u.username=? COLLATE NOCASE",
        "JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1",
    }
)
_USER_SELECT_ORDERS = frozenset(
    {
        "",
        "ORDER BY u.username COLLATE NOCASE",
        "ORDER BY u.id",
    }
)

# Authorization contract shared with the API and frontend. Every navigable
# page and meaningful feature has a named capability. Administrator access is
# intentionally immutable/full; non-admin role permissions are configurable from
# the Roles & permissions page and stored in the auth database. New capabilities
# default to administrator-only until explicitly enabled.
CAPABILITY_CATALOG: dict[str, dict[str, str | bool]] = {
    "page.dashboard": {"category": "Pages", "label": "Dashboard", "description": "Open the dashboard and researcher-safe overview widgets.", "researcher_default": True},
    "page.record": {"category": "Pages", "label": "Record view", "description": "Open a researcher-visible corpus record.", "researcher_default": True},
    "page.works": {"category": "Pages", "label": "Works", "description": "Browse works exposed by corpus databases.", "researcher_default": True},
    "page.search": {"category": "Pages", "label": "Search", "description": "Open corpus/global search.", "researcher_default": True},
    "page.annotations": {"category": "Pages", "label": "Annotations", "description": "Open the annotations workspace.", "researcher_default": True},
    "page.compare": {"category": "Pages", "label": "Compare", "description": "Compare researcher-visible records.", "researcher_default": True},
    "page.vector": {"category": "Pages", "label": "Corpus database", "description": "Browse researcher-visible vector collections.", "researcher_default": True},
    "page.research": {"category": "Pages", "label": "Research", "description": "Open the evidence-grounded Research workspace.", "researcher_default": True},
    "page.settings": {"category": "Pages", "label": "Appearance & settings", "description": "Open researcher-safe settings such as appearance.", "researcher_default": True},
    "page.records": {"category": "Pages", "label": "Loaded records", "description": "Open administrator loaded-record management.", "researcher_default": False},
    "page.pdf": {"category": "Pages", "label": "PDF Explorer", "description": "Open PDF extraction and exploration tools.", "researcher_default": False},
    "page.faq": {"category": "Pages", "label": "Response Library", "description": "Open the complete saved-response library workspace.", "researcher_default": False},
    "page.response_cache": {"category": "Pages", "label": "Response cache", "description": "Browse and manage the RAG response cache.", "researcher_default": False},
    "page.providers": {"category": "Pages", "label": "LLM profiles", "description": "Configure LLM provider profiles.", "researcher_default": False},
    "page.users": {"category": "Pages", "label": "Users", "description": "Manage user accounts.", "researcher_default": False},
    "page.languages": {"category": "Pages", "label": "Languages", "description": "Manage translation dictionaries.", "researcher_default": False},
    "page.roles": {"category": "Pages", "label": "Roles & permissions", "description": "Configure role permissions.", "researcher_default": False},
    "corpus.read": {"category": "Corpus", "label": "Read corpus", "description": "Read researcher-safe corpus records and work metadata.", "researcher_default": True},
    "corpus.search": {"category": "Corpus", "label": "Search corpus", "description": "Run keyword, filter, similarity, and MMR searches.", "researcher_default": True},
    "corpus.manage": {"category": "Corpus", "label": "Manage corpus", "description": "Create, modify, import, export, or delete corpus data and collections.", "researcher_default": False},
    "records.edit": {"category": "Corpus", "label": "Edit records", "description": "Change record fields, history, and metadata.", "researcher_default": False},
    "evidence.select": {"category": "Research", "label": "Select evidence", "description": "Pin corpus records into Research evidence packets.", "researcher_default": True},
    "rag.run": {"category": "Research", "label": "Run RAG", "description": "Start evidence-grounded RAG generation jobs.", "researcher_default": True},
    "rag.jobs.own": {"category": "Research", "label": "Manage own RAG jobs", "description": "View, cancel, and remove the signed-in user's RAG jobs.", "researcher_default": True},
    "providers.researcher.use": {"category": "Research", "label": "Use approved LLM profiles", "description": "Use administrator-approved researcher LLM profiles.", "researcher_default": True},
    "annotations.read": {"category": "Annotations", "label": "Read annotations", "description": "Read annotations attached to accessible corpus evidence.", "researcher_default": True},
    "annotations.write": {"category": "Annotations", "label": "Write annotations", "description": "Create and remove annotations on accessible evidence.", "researcher_default": True},
    "activity.read": {"category": "Dashboard", "label": "Recent activity", "description": "See activity for features and corpus works the account can access.", "researcher_default": True},
    "appearance.manage": {"category": "Settings", "label": "Appearance", "description": "Change personal browser appearance preferences.", "researcher_default": True},
    "i18n.read": {"category": "Settings", "label": "Use translations", "description": "Read installed interface dictionaries.", "researcher_default": True},
    "i18n.manage": {"category": "Administration", "label": "Manage languages", "description": "Install, edit, or remove interface dictionaries.", "researcher_default": False},
    "providers.manage": {"category": "Administration", "label": "Manage LLM profiles", "description": "Create and configure provider profiles and credentials.", "researcher_default": False},
    "users.manage": {"category": "Administration", "label": "Manage users", "description": "Create, disable, reset, and delete user accounts.", "researcher_default": False},
    "roles.manage": {"category": "Administration", "label": "Manage roles", "description": "Change role permission assignments.", "researcher_default": False},
}
DEFAULT_RESEARCHER_CAPABILITIES = frozenset(
    capability for capability, metadata in CAPABILITY_CATALOG.items()
    if bool(metadata.get("researcher_default"))
)

ADMIN_ONLY_CAPABILITIES = frozenset({
    "page.records", "page.pdf", "page.faq", "page.response_cache",
    "page.providers", "page.users", "page.languages", "page.roles",
    "corpus.manage", "records.edit", "i18n.manage", "providers.manage",
    "users.manage", "roles.manage",
})
SESSION_COOKIE = "derridai_session"
PBKDF2_ITERATIONS = 600_000
SESSION_DAYS = 14
_DUMMY_PASSWORD_SALT = "00" * 24
_DUMMY_PASSWORD_HASH = "00" * 32


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(actual, expected)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str
    role: Role
    role_name: str
    active: bool
    created_at: str
    updated_at: str
    last_login: str | None = None
    login_count: int = 0

    def public(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "role_name": self.role_name,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "login_count": self.login_count,
            "capabilities": capabilities_for_role(self.role),
        }


class AuthStore:
    def __init__(self) -> None:
        path = Path(getattr(settings, "auth_db_path", "/data/.home/derridai-auth.sqlite3")).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            now = _iso_now()
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    id TEXT PRIMARY KEY COLLATE NOCASE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    locked INTEGER NOT NULL DEFAULT 0,
                    builtin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login TEXT,
                    login_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                CREATE TABLE IF NOT EXISTS login_failures (
                    username_key TEXT PRIMARY KEY,
                    failures INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_login_failures_locked_until
                    ON login_failures(locked_until);
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY(role, capability)
                );
                CREATE TABLE IF NOT EXISTS user_role_assignments (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT
                );
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO roles(id,name,description,locked,builtin,created_at,updated_at) VALUES('admin','Administrator','Full application access. Administrator permissions are locked to prevent loss of administrative control.',1,1,?,?)",
                (now, now),
            )
            conn.execute(
                "INSERT OR IGNORE INTO roles(id,name,description,locked,builtin,created_at,updated_at) VALUES('researcher','Researcher','Default non-admin research role. Its permissions are configurable and enforced by both the API and interface.',0,1,?,?)",
                (now, now),
            )
            legacy_columns = {str(column[1]) for column in conn.execute("PRAGMA table_info(users)")}
            if "role" in legacy_columns:
                # Existing installations had a built-in-only users.role value.
                # Capture it exactly once, then remove the obsolete column so it
                # cannot diverge from the canonical assignment.
                conn.execute(
                    "INSERT OR IGNORE INTO user_role_assignments(user_id,role) SELECT id,role FROM users"
                )
                conn.execute("ALTER TABLE users DROP COLUMN role")
            role_rows = conn.execute("SELECT id FROM roles ORDER BY id").fetchall()
            for row in role_rows:
                role = str(row["id"])
                known = {
                    str(item[0]) for item in conn.execute(
                        "SELECT capability FROM role_permissions WHERE role=?", (role,)
                    ).fetchall()
                }
                if role == "researcher" and not known:
                    conn.executemany(
                        "INSERT OR REPLACE INTO role_permissions(role,capability,enabled) VALUES(?,?,?)",
                        [
                            (role, capability, 1 if capability in DEFAULT_RESEARCHER_CAPABILITIES else 0)
                            for capability in sorted(CAPABILITY_CATALOG)
                        ],
                    )
                    continue
                missing = sorted(set(CAPABILITY_CATALOG) - known)
                if missing and role != "admin":
                    conn.executemany(
                        "INSERT INTO role_permissions(role,capability,enabled) VALUES(?,?,0)",
                        [(role, capability) for capability in missing],
                    )

    @staticmethod
    def _row_user(row: sqlite3.Row | None) -> AuthUser | None:
        if row is None:
            return None
        keys = set(row.keys())
        effective_role = str(row["role"])
        role_name = str(
            row["role_name"]
            if "role_name" in keys and row["role_name"]
            else ("Administrator" if effective_role == "admin" else "Researcher" if effective_role == "researcher" else effective_role.replace("-", " ").title())
        )
        return AuthUser(
            id=int(row["id"]),
            username=str(row["username"]),
            role=effective_role,
            role_name=role_name,
            active=bool(row["active"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_login=(str(row["last_login"]) if "last_login" in keys and row["last_login"] else None),
            login_count=(int(row["login_count"] or 0) if "login_count" in keys else 0),
        )

    @staticmethod
    def _user_select(where: str = "", order: str = "") -> str:
        if where not in _USER_SELECT_WHERES or order not in _USER_SELECT_ORDERS:
            raise ValueError("Unsupported user query clause.")
        parts = [
            "SELECT u.*, a.role, r.name AS role_name",
            "FROM users u",
            "JOIN user_role_assignments a ON a.user_id=u.id",
            "JOIN roles r ON r.id=a.role",
        ]
        if where:
            parts.append(where)
        if order:
            parts.append(order)
        return " ".join(parts)

    def bootstrap_required(self) -> bool:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]) == 0

    def reset_to_fresh_install(self) -> dict[str, int]:
        """Return authentication to the first-run schema: no users, builtin roles only.

        Open connections stay valid. Tables are emptied in place so WAL files and
        the live AuthStore instance remain usable, then researcher permissions are
        restored to the shipped defaults.
        """
        now = _iso_now()
        with self._lock, self._connect() as conn:
            deleted_users = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
            deleted_roles = int(
                conn.execute(
                    "SELECT COUNT(*) FROM roles WHERE id NOT IN ('admin','researcher')"
                ).fetchone()[0]
            )
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM login_failures")
            conn.execute("DELETE FROM user_role_assignments")
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM role_permissions WHERE role NOT IN ('admin','researcher')")
            conn.execute("DELETE FROM roles WHERE id NOT IN ('admin','researcher')")
            try:
                conn.execute("DELETE FROM sqlite_sequence WHERE name='users'")
            except sqlite3.OperationalError:
                # sqlite_sequence exists only after at least one AUTOINCREMENT insert.
                pass
            conn.execute(
                "INSERT OR IGNORE INTO roles(id,name,description,locked,builtin,created_at,updated_at) VALUES('admin','Administrator','Full application access. Administrator permissions are locked to prevent loss of administrative control.',1,1,?,?)",
                (now, now),
            )
            conn.execute(
                "INSERT OR IGNORE INTO roles(id,name,description,locked,builtin,created_at,updated_at) VALUES('researcher','Researcher','Default non-admin research role. Its permissions are configurable and enforced by both the API and interface.',0,1,?,?)",
                (now, now),
            )
            conn.execute("DELETE FROM role_permissions WHERE role='researcher'")
            conn.executemany(
                "INSERT INTO role_permissions(role,capability,enabled) VALUES(?,?,?)",
                [
                    ("researcher", capability, 1 if capability in DEFAULT_RESEARCHER_CAPABILITIES else 0)
                    for capability in sorted(CAPABILITY_CATALOG)
                ],
            )
            conn.commit()
        return {"deleted_users": deleted_users, "deleted_custom_roles": deleted_roles}

    def bootstrap_admin(self, username: str, password: str) -> AuthUser:
        with self._lock:
            if not self.bootstrap_required():
                raise ValueError("Initial administrator has already been created.")
            return self.create_user(username, password, "admin")

    def role_ids(self) -> set[str]:
        with self._connect() as conn:
            return {str(row[0]) for row in conn.execute("SELECT id FROM roles").fetchall()}

    def role_exists(self, role: Role) -> bool:
        with self._connect() as conn:
            return conn.execute("SELECT 1 FROM roles WHERE id=?", (str(role),)).fetchone() is not None

    def create_role(self, name: str, description: str = "", clone_from: Role = "researcher") -> dict:
        clean_name = " ".join(str(name or "").split()).strip()
        if len(clean_name) < 2 or len(clean_name) > 80:
            raise ValueError("Role name must be between 2 and 80 characters.")
        clean_description = " ".join(str(description or "").split()).strip()[:500]
        source = str(clone_from or "researcher")
        if not self.role_exists(source):
            raise ValueError("Template role not found.")
        base = re.sub(r"[^a-z0-9]+", "-", clean_name.casefold()).strip("-")[:48] or "role"
        if base in {"admin", "administrator"}:
            base = "role-admin"
        now = _iso_now()
        with self._lock, self._connect() as conn:
            role_id = base
            suffix = 2
            while conn.execute("SELECT 1 FROM roles WHERE id=?", (role_id,)).fetchone() is not None:
                role_id = f"{base[:44]}-{suffix}"
                suffix += 1
            conn.execute(
                "INSERT INTO roles(id,name,description,locked,builtin,created_at,updated_at) VALUES(?,?,?,0,0,?,?)",
                (role_id, clean_name, clean_description, now, now),
            )
            source_permissions = set(self.capabilities_for_role(source)) if source != "admin" else set(DEFAULT_RESEARCHER_CAPABILITIES)
            source_permissions -= ADMIN_ONLY_CAPABILITIES
            conn.executemany(
                "INSERT INTO role_permissions(role,capability,enabled) VALUES(?,?,?)",
                [
                    (role_id, capability, 1 if capability in source_permissions else 0)
                    for capability in sorted(CAPABILITY_CATALOG)
                ],
            )
        roles, _ = self.role_definitions()
        return next(item for item in roles if item["id"] == role_id)

    def delete_role(self, role: Role) -> None:
        role = str(role)
        if role in {"admin", "researcher"}:
            raise ValueError("Built-in roles cannot be deleted.")
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT locked,builtin FROM roles WHERE id=?", (role,)).fetchone()
            if row is None:
                raise KeyError(role)
            if bool(row["locked"]) or bool(row["builtin"]):
                raise ValueError("This role cannot be deleted.")
            assigned = int(conn.execute("SELECT COUNT(*) FROM user_role_assignments WHERE role=?", (role,)).fetchone()[0])
            if assigned:
                raise ValueError("Reassign users from this role before deleting it.")
            conn.execute("DELETE FROM role_permissions WHERE role=?", (role,))
            conn.execute("DELETE FROM roles WHERE id=?", (role,))

    def create_user(self, username: str, password: str, role: Role) -> AuthUser:
        username = username.strip()
        role = str(role)
        if len(username) < 2 or len(username) > 80:
            raise ValueError("Username must be between 2 and 80 characters.")
        if len(password) < 6:
            raise ValueError("Password must contain at least 6 characters.")
        if not self.role_exists(role):
            raise ValueError("Selected role does not exist.")
        salt, digest = _hash_password(password)
        now = _iso_now()
        try:
            with self._lock, self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO users(username,password_salt,password_hash,active,created_at,updated_at) VALUES(?,?,?,1,?,?)",
                    (username, salt, digest, now, now),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO user_role_assignments(user_id,role) VALUES(?,?)",
                    (cursor.lastrowid, role),
                )
                row = conn.execute(self._user_select("WHERE u.id=?"), (cursor.lastrowid,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ValueError("A user with that username already exists.") from exc
        assert row is not None
        return self._row_user(row)

    @staticmethod
    def _login_key(username: str) -> str:
        return username.strip().casefold()

    @staticmethod
    def _parse_auth_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _login_throttle_settings() -> tuple[int, int]:
        limit = max(1, int(getattr(settings, "auth_login_max_failures", 5)))
        seconds = max(1, int(getattr(settings, "auth_login_lockout_seconds", 300)))
        return limit, seconds

    def login_lockout_remaining(self, username: str) -> int:
        """Whole seconds until this username may try again, or 0 when not locked.

        Keyed exactly like the failure counter, so a username that does not exist
        is reported the same way as one that does.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT locked_until FROM login_failures WHERE username_key=?",
                (self._login_key(username),),
            ).fetchone()
        locked_until = self._parse_auth_time(str(row["locked_until"]) if row and row["locked_until"] else None)
        if locked_until is None:
            return 0
        remaining = (locked_until - datetime.now(UTC)).total_seconds()
        return int(remaining) + 1 if remaining > 0 else 0

    def authenticate(self, username: str, password: str) -> AuthUser | None:
        username_clean = username.strip()
        username_key = self._login_key(username_clean)
        limit, lockout_seconds = self._login_throttle_settings()
        now_dt = datetime.now(UTC)
        now = now_dt.isoformat()
        with self._lock, self._connect() as conn:
            # Serialize failure-counter updates across AuthStore instances, not
            # merely threads sharing this Python object.
            conn.execute("BEGIN IMMEDIATE")
            throttle = conn.execute(
                "SELECT failures,locked_until FROM login_failures WHERE username_key=?",
                (username_key,),
            ).fetchone()
            row = conn.execute(
                self._user_select("WHERE u.username=? COLLATE NOCASE"),
                (username_clean,),
            ).fetchone()

            # Spend the same PBKDF2 work for an unknown username as for a known
            # account, avoiding a cheap username-existence timing distinction.
            if row is None:
                password_valid = _verify_password(
                    password, _DUMMY_PASSWORD_SALT, _DUMMY_PASSWORD_HASH
                )
                password_valid = False
            else:
                password_valid = _verify_password(
                    password, str(row["password_salt"]), str(row["password_hash"])
                )
                password_valid = password_valid and bool(row["active"])

            locked_until = self._parse_auth_time(
                str(throttle["locked_until"]) if throttle and throttle["locked_until"] else None
            )
            if locked_until is not None and locked_until > now_dt:
                return None

            if not password_valid or row is None:
                prior_failures = int(throttle["failures"] or 0) if throttle else 0
                # An expired lock begins a fresh failure window.
                if locked_until is not None and locked_until <= now_dt:
                    prior_failures = 0
                failures = prior_failures + 1
                next_locked_until = (
                    (now_dt + timedelta(seconds=lockout_seconds)).isoformat()
                    if failures >= limit
                    else None
                )
                conn.execute(
                    """
                    INSERT INTO login_failures(username_key,failures,locked_until,updated_at)
                    VALUES(?,?,?,?)
                    ON CONFLICT(username_key) DO UPDATE SET
                        failures=excluded.failures,
                        locked_until=excluded.locked_until,
                        updated_at=excluded.updated_at
                    """,
                    (username_key, failures, next_locked_until, now),
                )
                return None

            conn.execute("DELETE FROM login_failures WHERE username_key=?", (username_key,))
            conn.execute(
                "UPDATE users SET last_login=?, login_count=COALESCE(login_count,0)+1 WHERE id=?",
                (now, int(row["id"])),
            )
            row = conn.execute(self._user_select("WHERE u.id=?"), (int(row["id"]),)).fetchone()
            return self._row_user(row)

    def record_login(self, user_id: int) -> AuthUser:
        """Record a successful sign-in (used by first-run bootstrap)."""
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE users SET last_login=?, login_count=COALESCE(login_count,0)+1 WHERE id=?",
                (now, user_id),
            )
            row = conn.execute(self._user_select("WHERE u.id=?"), (user_id,)).fetchone()
        user = self._row_user(row)
        if user is None:
            raise KeyError(user_id)
        return user

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(48)
        now = datetime.now(UTC)
        expires = now + timedelta(days=SESSION_DAYS)
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now.isoformat(),))
            conn.execute(
                "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                (_token_hash(token), user_id, now.isoformat(), expires.isoformat()),
            )
        return token

    def user_for_session(self, token: str | None) -> AuthUser | None:
        if not token:
            return None
        now = _iso_now()
        with self._connect() as conn:
            row = conn.execute(
                self._user_select(
                    "JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1"
                ),
                (_token_hash(token), now),
            ).fetchone()
            return self._row_user(row)

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))

    def list_users(self) -> list[AuthUser]:
        with self._connect() as conn:
            rows = conn.execute(self._user_select(order="ORDER BY u.username COLLATE NOCASE")).fetchall()
            return [self._row_user(row) for row in rows if row is not None]

    def get_user(self, user_id: int) -> AuthUser | None:
        with self._connect() as conn:
            return self._row_user(conn.execute(self._user_select("WHERE u.id=?"), (user_id,)).fetchone())

    def update_user(self, user_id: int, *, role: Role | None = None, active: bool | None = None, password: str | None = None) -> AuthUser:
        current = self.get_user(user_id)
        if current is None:
            raise KeyError(user_id)
        if role is not None and not self.role_exists(str(role)):
            raise ValueError("Selected role does not exist.")
        if password is not None and len(password) < 6:
            raise ValueError("Password must contain at least 6 characters.")
        next_role = str(role or current.role)
        next_active = current.active if active is None else active
        if current.role == "admin" and current.active and (next_role != "admin" or not next_active):
            if self._active_admin_count() <= 1:
                raise ValueError("At least one active administrator is required.")
        now = _iso_now()
        with self._lock, self._connect() as conn:
            if password is not None:
                salt, digest = _hash_password(password)
                conn.execute(
                    "UPDATE users SET active=?, updated_at=?, password_salt=?, password_hash=? WHERE id=?",
                    (int(next_active), now, salt, digest, user_id),
                )
            else:
                conn.execute(
                    "UPDATE users SET active=?, updated_at=? WHERE id=?",
                    (int(next_active), now, user_id),
                )
            conn.execute(
                "INSERT OR REPLACE INTO user_role_assignments(user_id,role) VALUES(?,?)",
                (user_id, next_role),
            )
            if not next_active:
                conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            row = conn.execute(self._user_select("WHERE u.id=?"), (user_id,)).fetchone()
        assert row is not None
        return self._row_user(row)

    def delete_user(self, user_id: int) -> None:
        current = self.get_user(user_id)
        if current is None:
            raise KeyError(user_id)
        if current.role == "admin" and current.active and self._active_admin_count() <= 1:
            raise ValueError("The last active administrator cannot be deleted.")
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))

    def snapshot_users(self) -> list[dict]:
        """Return a backup-safe logical user snapshot. Sessions are excluded."""
        with self._connect() as conn:
            rows = conn.execute(self._user_select(order="ORDER BY u.id")).fetchall()
            return [
                {
                    "id": int(row["id"]),
                    "username": str(row["username"]),
                    "password_salt": str(row["password_salt"]),
                    "password_hash": str(row["password_hash"]),
                    "role": str(row["role"]),
                    "active": bool(row["active"]),
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]),
                    "last_login": (str(row["last_login"]) if row["last_login"] else None),
                    "login_count": int(row["login_count"] or 0),
                }
                for row in rows
            ]

    def snapshot_roles(self) -> list[dict]:
        roles, _ = self.role_definitions()
        return [
            {
                "id": role["id"],
                "name": role["name"],
                "description": role["description"],
                "locked": bool(role["locked"]),
                "builtin": bool(role.get("builtin", False)),
                "permissions": list(role.get("permissions") or []),
            }
            for role in roles
        ]

    def restore_roles(self, roles: list[dict]) -> int:
        if not isinstance(roles, list):
            raise ValueError("Role backup payload is invalid.")
        restored = 0
        now = _iso_now()
        with self._lock, self._connect() as conn:
            for raw in roles:
                if not isinstance(raw, dict):
                    continue
                role_id = str(raw.get("id") or "").strip().lower()
                if role_id in {"", "admin"}:
                    continue
                if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", role_id):
                    raise ValueError(f"Invalid role id in backup: {role_id}")
                name = " ".join(str(raw.get("name") or role_id).split())[:80]
                description = " ".join(str(raw.get("description") or "").split())[:500]
                builtin = 1 if role_id == "researcher" else 0
                conn.execute(
                    "INSERT INTO roles(id,name,description,locked,builtin,created_at,updated_at) VALUES(?,?,?,0,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,updated_at=excluded.updated_at",
                    (role_id, name, description, builtin, now, now),
                )
                permissions = {str(item) for item in (raw.get("permissions") or []) if str(item) in CAPABILITY_CATALOG}
                permissions -= ADMIN_ONLY_CAPABILITIES
                conn.executemany(
                    "INSERT OR REPLACE INTO role_permissions(role,capability,enabled) VALUES(?,?,?)",
                    [(role_id, capability, 1 if capability in permissions else 0) for capability in sorted(CAPABILITY_CATALOG)],
                )
                restored += 1
        return restored

    def restore_users(self, users: list[dict]) -> int:
        if not isinstance(users, list) or not users:
            raise ValueError("User backup must contain at least one account.")
        normalized: list[tuple] = []
        active_admins = 0
        seen_names: set[str] = set()
        known_roles = self.role_ids()
        for raw in users:
            if not isinstance(raw, dict):
                raise ValueError("User backup contains an invalid account entry.")
            username = str(raw.get("username") or "").strip()
            role = str(raw.get("role") or "")
            active = bool(raw.get("active", True))
            if len(username) < 2 or role not in known_roles:
                raise ValueError("User backup contains an invalid username or role.")
            lowered = username.casefold()
            if lowered in seen_names:
                raise ValueError("User backup contains duplicate usernames.")
            seen_names.add(lowered)
            salt = str(raw.get("password_salt") or "")
            digest = str(raw.get("password_hash") or "")
            try:
                bytes.fromhex(salt); bytes.fromhex(digest)
            except ValueError as exc:
                raise ValueError("User backup contains invalid password credentials.") from exc
            if role == "admin" and active:
                active_admins += 1
            normalized.append((
                int(raw.get("id") or 0) or None, username, salt, digest, role, int(active),
                str(raw.get("created_at") or _iso_now()), str(raw.get("updated_at") or _iso_now()),
                (str(raw.get("last_login")) if raw.get("last_login") else None),
                max(0, int(raw.get("login_count") or 0)),
            ))
        if active_admins < 1:
            raise ValueError("User backup must contain at least one active administrator.")
        with self._lock, self._connect() as conn:
            existing_sessions = [tuple(row) for row in conn.execute(
                "SELECT token_hash,user_id,created_at,expires_at FROM sessions WHERE expires_at>?",
                (_iso_now(),),
            ).fetchall()]
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM user_role_assignments")
            conn.execute("DELETE FROM users")
            restored_ids: set[int] = set()
            for user_id, username, salt, digest, role, active, created_at, updated_at, last_login, login_count in normalized:
                cursor = conn.execute(
                    "INSERT INTO users(id,username,password_salt,password_hash,active,created_at,updated_at,last_login,login_count) VALUES(?,?,?,?,?,?,?,?,?)",
                    (user_id, username, salt, digest, active, created_at, updated_at, last_login, login_count),
                )
                restored_id = int(user_id or cursor.lastrowid)
                restored_ids.add(restored_id)
                conn.execute(
                    "INSERT INTO user_role_assignments(user_id,role) VALUES(?,?)",
                    (restored_id, role),
                )
            for token_hash, user_id, created_at, expires_at in existing_sessions:
                if int(user_id) in restored_ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                        (token_hash, user_id, created_at, expires_at),
                    )
        return len(normalized)

    def capabilities_for_role(self, role: Role) -> list[str]:
        if role == "admin":
            return ["*"]
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT capability FROM role_permissions WHERE role=? AND enabled=1 ORDER BY capability",
                (str(role),),
            ).fetchall()
        return [str(row["capability"]) for row in rows if str(row["capability"]) in CAPABILITY_CATALOG]

    def role_has_capability(self, role: Role, capability: str) -> bool:
        if role == "admin":
            return True
        return capability in set(self.capabilities_for_role(role))

    def role_definitions(self) -> tuple[list[dict], list[dict]]:
        capabilities = [
            {
                "id": capability,
                "category": str(metadata.get("category") or "Other"),
                "label": str(metadata.get("label") or capability),
                "description": str(metadata.get("description") or ""),
                "configurable": capability not in ADMIN_ONLY_CAPABILITIES,
            }
            for capability, metadata in CAPABILITY_CATALOG.items()
        ]
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id,name,description,locked,builtin FROM roles ORDER BY CASE id WHEN 'admin' THEN 0 WHEN 'researcher' THEN 1 ELSE 2 END,name COLLATE NOCASE"
            ).fetchall()
        roles = []
        for row in rows:
            role_id = str(row["id"])
            roles.append({
                "id": role_id,
                "name": str(row["name"]),
                "description": str(row["description"] or ""),
                "locked": bool(row["locked"]),
                "builtin": bool(row["builtin"]),
                "permissions": ["*"] if role_id == "admin" else self.capabilities_for_role(role_id),
            })
        return roles, capabilities

    def set_role_permissions(self, role: Role, permissions: list[str]) -> list[str]:
        role = str(role)
        if role == "admin":
            raise ValueError("Administrator permissions are fixed to full access.")
        with self._connect() as conn:
            row = conn.execute("SELECT locked FROM roles WHERE id=?", (role,)).fetchone()
        if row is None:
            raise ValueError("Unknown role.")
        if bool(row["locked"]):
            raise ValueError("This role's permissions are locked.")
        allowed = {str(item) for item in permissions if str(item) in CAPABILITY_CATALOG}
        allowed -= ADMIN_ONLY_CAPABILITIES
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO role_permissions(role,capability,enabled) VALUES(?,?,?)",
                [
                    (role, capability, 1 if capability in allowed else 0)
                    for capability in sorted(CAPABILITY_CATALOG)
                ],
            )
        return sorted(allowed)

    def _active_admin_count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM users u JOIN user_role_assignments a ON a.user_id=u.id WHERE a.role='admin' AND u.active=1").fetchone()[0])


auth_store = AuthStore()

def capabilities_for_role(role: Role) -> list[str]:
    return auth_store.capabilities_for_role(role)

def role_has_capability(role: Role, capability: str) -> bool:
    return auth_store.role_has_capability(role, capability)
