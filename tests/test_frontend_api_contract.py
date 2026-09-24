# Copyright 2026 Aaron John Schlosser, PhD.
"""Contract tests binding frontend API wrappers to FastAPI routes and methods."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.application import create_app  # noqa: E402
from scripts.check_frontend_api_contract import contract_mismatches  # noqa: E402

pytestmark = pytest.mark.contract


def test_frontend_api_calls_exist_in_fastapi_openapi() -> None:
    """Every typed frontend request must target a real FastAPI method and route."""
    mismatches = contract_mismatches(create_app().openapi())
    assert mismatches == [], "\n".join(mismatches)
