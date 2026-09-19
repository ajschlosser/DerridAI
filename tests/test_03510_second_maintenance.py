"""Server-side normalization of researcher provider-profile generation options (release 0.35.10).

Why: researcher accounts run RAG through an administrator-approved provider profile.
Its generation options are stored as strings (from forms or JSON) and must be
converted to real types on the server so the browser can never supply or alter them.
How: imports the helper straight from app.main and feeds it string values.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]




def test_researcher_static_profile_generation_is_normalized_server_side():
    """Strings from a stored profile become typed generation options.

    What: "8192" -> int, "0.2" -> float, "false" -> bool, a JSON string -> dict, and
    "10m" stays a string (Ollama's keep_alive duration).
    Why: Ollama rejects or misinterprets numeric options sent as strings, and an
    unparsed extra_options string would otherwise be silently ignored.
    """
    if str(ROOT/"api") not in sys.path:
        sys.path.insert(0,str(ROOT/"api"))
    from app.main import _profile_generation_options
    values=_profile_generation_options({
        "num_ctx":"8192",
        "temperature":"0.2",
        "think":"false",
        "extra_options":'{"repeat_last_n": 128}',
        "keep_alive":"10m",
    })
    assert values["num_ctx"] == 8192
    assert values["temperature"] == 0.2
    assert values["think"] is False
    assert values["extra_options"] == {"repeat_last_n":128}
    assert values["keep_alive"] == "10m"










