# Copyright 2026 Aaron John Schlosser, PhD.
"""Generate a locale's researcher text policy with the selected LLM provider."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .content_filter import POLICY_VERSION, normalize_content_policy
from .models import OllamaTouchupOptions
from .rag import _extract_json, chat_complete

POLICY_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["blocked_terms", "contextual_terms"],
    "properties": {
        "blocked_terms": {
            "type": "array",
            "minItems": 8,
            "maxItems": 150,
            "items": {"type": "string"},
        },
        "contextual_terms": {
            "type": "array",
            "maxItems": 24,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["term"],
                "properties": {
                    "term": {"type": "string"},
                    "allow_title_case": {"type": "boolean"},
                    "allow_if_surrounding": {"type": "array", "items": {"type": "string"}},
                    "allow_if_before_markers": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


def _policy_prompt(code: str) -> str:
    return (
        "You are compiling a researcher-account text policy for DerridAI, a scholarly research tool. "
        f"The target locale is {code}. Return one JSON object with two arrays: blocked_terms and contextual_terms. "
        "blocked_terms lists lowercase single-token vulgarities, sexual insults, and slurs that are abusive in this locale. "
        "Include racial, ethnic, religious, homophobic, transphobic, and ableist slurs actually used in the locale. "
        "Do not include ordinary scholarly vocabulary, given names, book titles, or words that are not abusive. "
        "contextual_terms is for tokens that are abusive in some uses and innocent in others. "
        "For those, set allow_title_case when the Title Case form is a common personal name, "
        "allow_if_surrounding for nearby gloss words that mark a non-abusive sense, "
        "and allow_if_before_markers for quoted lexical discussion such as 'word ' or 'term '. "
        "Every term must be a single token of letters, optional apostrophes, or hyphens. "
        "Return 20 to 80 blocked terms and at most 12 contextual terms. Do not explain."
    )


def generate_content_policy(
    *,
    code: str,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    generation: OllamaTouchupOptions | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    raw = chat_complete(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        prompt=_policy_prompt(code),
        options=generation,
        json_mode=True,
        json_schema=POLICY_JSON_SCHEMA,
        schema_name="derridai_researcher_content_policy",
        cancelled=cancelled,
    )
    parsed = _extract_json(raw)
    policy = normalize_content_policy(parsed, require_ready=True)
    policy["generated_at"] = datetime.now(timezone.utc).isoformat()
    policy["source"] = "llm-generated"
    policy["provider"] = provider
    policy["model"] = model
    policy["version"] = POLICY_VERSION
    return policy
