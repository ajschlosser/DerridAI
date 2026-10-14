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

"""Server-side normalization of researcher provider-profile generation options.

Why: researcher accounts run RAG through an administrator-approved provider profile.
Its generation options may be stored as strings and must be converted to real types
on the server so the browser cannot supply or alter them.
"""

from __future__ import annotations

from app.provider_profile_options import profile_generation_options


def test_researcher_static_profile_generation_is_normalized_server_side():
    """Stored profile strings become correctly typed generation options."""
    values = profile_generation_options(
        {
            "num_ctx": "8192",
            "temperature": "0.2",
            "think": "false",
            "extra_options": '{"repeat_last_n": 128}',
            "keep_alive": "10m",
        }
    )

    assert values["num_ctx"] == 8192
    assert values["temperature"] == 0.2
    assert values["think"] is False
    assert values["extra_options"] == {"repeat_last_n": 128}
    assert values["keep_alive"] == "10m"
