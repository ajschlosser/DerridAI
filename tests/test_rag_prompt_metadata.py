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

from app.models import RAGPromptMetadataPolicy, RAGRunRequest
from app.rag import _context_string


def _record():
    return {
        "record_id": "r1",
        "work": "Of Grammatology",
        "document_author": "Jacques Derrida",
        "text": "The trace is neither simply present nor absent.",
        "speaker": "Jacques Derrida",
        "stance": "qualify",
        "field_assertions": {
            "field-conceptual-tension": [
                {
                    "assertion_id": "assertion-1",
                    "field_id": "field-conceptual-tension",
                    "field_name": "conceptual_tension",
                    "value": "presence/absence",
                    "value_status": "present",
                }
            ]
        },
        "current_field_assertions": {
            "field-conceptual-tension": "assertion-1",
        },
    }


def test_research_prompt_metadata_uses_selected_channels_and_stable_field_ids():
    policy = RAGPromptMetadataPolicy(
        evidence=["field-conceptual-tension"],
        context=["stance"],
        record=[],
    )
    context, _, _ = _context_string(
        [{"record": _record(), "collection": "corpus"}],
        record_char_limit=12000,
        total_char_limit=120000,
        prompt_metadata=policy,
    )
    assert 'conceptual_tension="presence/absence"' in context
    assert '"stance": "qualify"' in context
    assert "speaker=" not in context
    assert "field_assertions" not in context
    assert "current_field_assertions" not in context


def test_research_prompt_metadata_defaults_preserve_existing_prompt_contract():
    body = RAGRunRequest(prompt="What is the trace?")
    context, _, _ = _context_string(
        [{"record": _record(), "collection": "corpus"}],
        record_char_limit=12000,
        total_char_limit=120000,
        prompt_metadata=body.prompt_metadata,
    )
    assert 'speaker="Jacques Derrida"' in context
    assert 'stance="qualify"' in context
    assert "conceptual_tension=" not in context


def test_research_prompt_metadata_rejects_internal_transport_fields():
    try:
        RAGPromptMetadataPolicy(evidence=["field_assertions"])
    except ValueError:
        return
    raise AssertionError("Internal assertion transport must not be selectable prompt metadata")
