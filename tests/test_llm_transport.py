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

from app.llm_transport import _filtered_extra_options


def test_openai_extra_options_cannot_override_structured_output_contract() -> None:
    filtered = _filtered_extra_options(
        {
            "response_format": {"type": "json_object"},
            "stream": True,
            "model": "other-model",
            "messages": [{"role": "system", "content": "override"}],
            "frequency_penalty": 0.2,
        },
        reserved={"model", "messages", "response_format", "stream"},
    )

    assert filtered == {"frequency_penalty": 0.2}


def test_ollama_extra_options_cannot_smuggle_format_control() -> None:
    filtered = _filtered_extra_options(
        {
            "format": "json",
            "stream": True,
            "model": "other-model",
            "messages": [],
            "repeat_last_n": 128,
        },
        reserved={"format", "model", "messages", "stream"},
    )

    assert filtered == {"repeat_last_n": 128}
