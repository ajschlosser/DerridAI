# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

import fitz


def extract_pdf_text(data: bytes, page: int | None = None) -> dict[str, Any]:
    if not data:
        raise ValueError("The uploaded PDF was empty.")

    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open PDF: {exc}") from exc

    try:
        total_pages = document.page_count
        if total_pages < 1:
            return {
                "total_pages": 0,
                "pages": [],
                "has_text": False,
                "engine": "pymupdf",
            }

        if page is not None:
            if page < 1 or page > total_pages:
                raise ValueError(
                    f"Page must be between 1 and {total_pages}."
                )
            indexes = [page - 1]
        else:
            indexes = range(total_pages)

        pages = []
        has_text = False
        for index in indexes:
            text = document.load_page(index).get_text("text", sort=True)
            text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
            if text:
                has_text = True
            pages.append({
                "page": index + 1,
                "text": text,
            })

        return {
            "total_pages": total_pages,
            "pages": pages,
            "has_text": has_text,
            "engine": "pymupdf",
        }
    finally:
        document.close()
