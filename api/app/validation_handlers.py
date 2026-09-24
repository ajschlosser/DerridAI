# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a stable, concise validation error while logging full details."""
    errors = exc.errors()
    fields: list[str] = []
    for error in errors:
        location = [
            str(part)
            for part in error.get("loc", ())
            if str(part) not in {"body", "query", "path"}
        ]
        label = ".".join(location) if location else "request"
        if label not in fields:
            fields.append(label)

    logger.warning(
        "Request validation failed for %s: %s",
        getattr(request, "url", "request"),
        errors,
    )

    message = "Some submitted data is invalid. Review the highlighted fields and try again."
    if fields:
        message += " Fields: " + ", ".join(fields[:8])
        if len(fields) > 8:
            message += "…"

    return JSONResponse(
        status_code=422,
        content={
            "detail": message,
            "code": "request_validation_error",
            "fields": fields[:50],
        },
    )
