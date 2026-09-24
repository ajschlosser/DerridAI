# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json

_PROFILE_GENERATION_INT_KEYS = {"num_ctx", "num_predict", "top_k", "seed", "mirostat"}
_PROFILE_GENERATION_FLOAT_KEYS = {
    "temperature",
    "top_p",
    "min_p",
    "repeat_penalty",
    "mirostat_eta",
    "mirostat_tau",
}


def profile_generation_options(profile: dict[str, object]) -> dict[str, object]:
    """Normalize generation options stored with a provider profile.

    Provider-profile forms may persist optional controls as strings, including
    JSON-encoded extra options. Converting them at this server-owned trust
    boundary keeps researcher runs independent of browser-supplied execution
    settings and gives downstream Pydantic models correctly typed values.
    """
    result: dict[str, object] = {}

    for key in _PROFILE_GENERATION_INT_KEYS:
        value = profile.get(key)
        if value in (None, ""):
            continue
        try:
            result[key] = int(float(str(value).strip()))
        except (TypeError, ValueError):
            continue

    for key in _PROFILE_GENERATION_FLOAT_KEYS:
        value = profile.get(key)
        if value in (None, ""):
            continue
        try:
            result[key] = float(str(value).strip())
        except (TypeError, ValueError):
            continue

    think = profile.get("think")
    if think not in (None, ""):
        if isinstance(think, bool):
            result["think"] = think
        else:
            normalized = str(think).strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                result["think"] = True
            elif normalized in {"false", "0", "no", "off"}:
                result["think"] = False
            elif normalized in {"low", "medium", "high"}:
                result["think"] = normalized

    keep_alive = profile.get("keep_alive")
    if keep_alive not in (None, ""):
        result["keep_alive"] = str(keep_alive).strip()

    extra_options = profile.get("extra_options")
    if isinstance(extra_options, dict):
        result["extra_options"] = extra_options
    elif isinstance(extra_options, str) and extra_options.strip():
        try:
            parsed = json.loads(extra_options)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            result["extra_options"] = parsed

    return result
