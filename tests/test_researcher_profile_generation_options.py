"""Server-side normalization of researcher provider-profile generation options."""

from app.routers.jobs import _profile_generation_options


def test_researcher_static_profile_generation_is_normalized_server_side():
    """Persisted string values become typed model-generation options."""
    values = _profile_generation_options(
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
