# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
import sys
import tempfile
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[1]
_api_root = str(_repo_root / "api")
if _api_root not in sys.path:
    # Test modules must not rely on another test being collected first to make
    # the application package importable.
    sys.path.insert(0, _api_root)

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

# The evidence-suggestion cascade's last-resort stage makes a real provider call from inside
# metadata reconciliation. A test that does not stub that provider call must never reach the
# network by default; a test exercising the LLM stage stubs `_chat_json` and opts back in via
# the request's own `evidence_cascade_llm_enabled` flag.
os.environ.setdefault("METADATA_EVIDENCE_CASCADE_LLM_ENABLED", "false")

def pytest_report_header() -> str:
    """Expose the isolated storage root in verbose local runs."""
    return f"DerridAI test storage: {Path(_root).name}"
