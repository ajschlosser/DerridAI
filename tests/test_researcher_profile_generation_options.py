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
