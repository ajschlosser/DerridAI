# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json
from typing import Any

from fastapi import Response

from .corpus_reviewer_helpers import _present_for_reviewer
from .reviewer_context import current_reviewer


def scrub_second_opinions(node: Any) -> bool:
    """Hide first-review answers from a reviewer who owes an independent review.

    Corpus responses can nest records under several keys. Walking the decoded
    payload here keeps the privacy rule independent of whichever endpoint
    produced the record. Returns True when at least one value was hidden.
    """
    hidden = False
    if isinstance(node, dict):
        if "record_id" in node and isinstance(node.get("second_opinion"), dict):
            before = json.dumps(node, default=str)
            _present_for_reviewer(node)
            hidden = json.dumps(node, default=str) != before
        for value in node.values():
            hidden = scrub_second_opinions(value) or hidden
    elif isinstance(node, list):
        for item in node:
            hidden = scrub_second_opinions(item) or hidden
    return hidden


async def hide_pending_second_opinions(response: Response) -> Response:
    """Filter corpus JSON responses without changing unrelated response bodies.

    The byte pre-check avoids decoding every corpus response. Content-Length and
    Content-Type are rebuilt because scrubbing can change the serialized body.
    """
    if "application/json" not in str(response.headers.get("content-type", "")):
        return response

    if hasattr(response, "body_iterator"):
        body = b"".join([chunk async for chunk in response.body_iterator])
    else:
        body = bytes(response.body)

    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"content-length", "content-type"}
    }

    if b"second_opinion" in body:
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        if (
            payload is not None
            and current_reviewer.get()
            and scrub_second_opinions(payload)
        ):
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")

    return Response(
        content=body,
        status_code=response.status_code,
        headers=headers,
        media_type="application/json",
    )
