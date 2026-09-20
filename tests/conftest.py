# Copyright 2026 Aaron John Schlosser, PhD.
"""Give the backend throwaway storage before any test imports the app.

The app reads CHROMA_DATA_ROOT, CHROMA_PATH, AUTH_DB_PATH, and SYSTEM_DB_PATH when it is imported and
defaults to /data, which does not exist (or is not writable) on a developer machine. Setting them here
means `pytest` works with nothing exported. That matters beyond convenience: docker-compose.yml
interpolates the same variable names, so exporting them in a shell to run the tests silently changes
what a later `docker compose up` does (the API container then crash-loops on a host path).

Values that are already set (for example by CI) are left alone.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

_root = tempfile.mkdtemp(prefix="derridai-tests-")
atexit.register(shutil.rmtree, _root, ignore_errors=True)

os.environ.setdefault("CHROMA_DATA_ROOT", _root)
os.environ.setdefault("CHROMA_PATH", os.path.join(_root, "chroma"))
os.environ.setdefault("AUTH_DB_PATH", os.path.join(_root, ".home", "derridai-auth.sqlite3"))
os.environ.setdefault("SYSTEM_DB_PATH", os.path.join(_root, ".home", "derridai-system.sqlite3"))
