# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from .application import create_app

# ASGI entry point used by Uvicorn, tests, and Docker.
app = create_app()
