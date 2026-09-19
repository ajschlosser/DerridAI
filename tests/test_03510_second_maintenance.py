from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]




def test_researcher_static_profile_generation_is_normalized_server_side():
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










