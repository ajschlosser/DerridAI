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

"""Contract tests binding frontend API wrappers to FastAPI routes and methods."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from app.application import create_app  # noqa: E402

from scripts.check_frontend_api_contract import contract_mismatches  # noqa: E402

pytestmark = pytest.mark.contract


def test_frontend_api_calls_exist_in_fastapi_openapi() -> None:
    """Every typed frontend request must target a real FastAPI method and route."""
    mismatches = contract_mismatches(create_app().openapi())
    assert mismatches == [], "\n".join(mismatches)
