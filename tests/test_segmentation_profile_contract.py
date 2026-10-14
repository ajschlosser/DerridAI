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

"""Profile-owned segmentation semantics.

Why: segmentation signals belong to an explicit corpus profile rather than the
generic MetadataSchema. Adding a custom scholarly field must not silently turn it
into a record-boundary signal.
How: characterize the built-in profile contract, the boundary transport, and the
prompt rendering used by segmentation execution.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.corpus_models import (
    CORPUS_PROFILES,
    PROFILE_VERSION,
    SCHOLARLY_SEGMENTATION_DIMENSIONS,
    BatchBoundaryDecisionModel,
    segmentation_dimensions_for_profile,
)
from app.corpus_segmentation_execution import _boundary_dimension_prompt_phrase


def test_default_profile_explicitly_owns_segmentation_dimensions():
    """The current scholarly boundary roles are declared by the profile contract."""
    profile = CORPUS_PROFILES[PROFILE_VERSION]

    assert segmentation_dimensions_for_profile(profile) == SCHOLARLY_SEGMENTATION_DIMENSIONS
    assert segmentation_dimensions_for_profile(profile) == (
        "speaker",
        "position_holder",
        "stance",
        "target",
        "quotation_frame",
        "discourse_role",
        "argumentative_move",
    )
    assert "conceptual_tension" not in segmentation_dimensions_for_profile(profile)


def test_boundary_transport_rejects_unrelated_schema_fields():
    """An ordinary custom metadata field cannot masquerade as a segmentation signal."""
    with pytest.raises(ValidationError):
        BatchBoundaryDecisionModel.model_validate(
            {
                "after": "b1",
                "decision": "split",
                "confidence": 0.9,
                "changes": ["conceptual_tension"],
            }
        )


def test_profile_driven_prompt_phrase_preserves_existing_contract_text():
    """Generating prompt prose from the profile does not change v9 prompt semantics."""
    dimensions = segmentation_dimensions_for_profile(CORPUS_PROFILES[PROFILE_VERSION])

    assert _boundary_dimension_prompt_phrase(dimensions) == (
        "speaker, position holder, stance, target, quotation frame, discourse role, "
        "or argumentative move"
    )
