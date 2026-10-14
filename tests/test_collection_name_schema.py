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

"""API schema contract for vector-collection creation.

Why: a collection name becomes a ChromaDB collection and appears in URLs, backups,
and manifests, so the API must reject names Chroma cannot store (too short,
IP-address-shaped, containing spaces) before any storage call is made.
How: constructs the Pydantic request model directly; no server, Chroma, or disk.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))








def test_collection_name_contract_is_validated_in_api_schema():
    """Reject invalid collection names at the schema layer and apply safe defaults.

    What: "x" (too short), "192.168.1.1" (IP-shaped) and "bad name" (space) must raise
    ValidationError; a valid name such as "derrida-primary" is accepted.
    Why the defaults matter: retrieval_mode="hybrid" and distance_metric="cosine" are
    the documented defaults, and changing them silently would change search behavior
    for every newly created collection.
    """
    from app.models import StoreCreate

    with pytest.raises(ValidationError):
        StoreCreate(name="x")
    with pytest.raises(ValidationError):
        StoreCreate(name="192.168.1.1")
    with pytest.raises(ValidationError):
        StoreCreate(name="bad name")
    model = StoreCreate(name="derrida-primary")
    assert model.retrieval_mode == "hybrid"
    assert model.distance_metric == "cosine"







