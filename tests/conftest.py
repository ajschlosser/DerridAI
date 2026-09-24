# Copyright 2026 Aaron John Schlosser, PhD.
"""Global backend-test isolation and taxonomy.

Every pytest process receives throwaway storage before application modules are
imported. Under pytest-xdist each worker gets a distinct root so SQLite,
filesystem corpus state, and embedded-vector paths cannot collide.

Existing tests without an explicit behavioral category remain regression tests.
New boundary-oriented suites opt into the registered markers in pytest.ini; this
avoids pretending that historical persistence or route tests are pure units.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

_worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
_root = tempfile.mkdtemp(prefix=f"derridai-tests-{_worker}-")
atexit.register(shutil.rmtree, _root, ignore_errors=True)

_storage = {
    "CHROMA_DATA_ROOT": _root,
    "CHROMA_PATH": os.path.join(_root, "chroma"),
    "AUTH_DB_PATH": os.path.join(_root, ".home", "derridai-auth.sqlite3"),
    "SYSTEM_DB_PATH": os.path.join(_root, ".home", "derridai-system.sqlite3"),
}
for _name, _value in _storage.items():
    if "PYTEST_XDIST_WORKER" in os.environ:
        # A worker must never inherit another worker/controller's shared path.
        os.environ[_name] = _value
    else:
        os.environ.setdefault(_name, _value)

def pytest_report_header() -> str:
    """Expose the isolated storage root in verbose local runs."""
    return f"DerridAI test storage: {Path(_root).name}"
