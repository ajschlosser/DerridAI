"""Explicit context passed between corpus construction stages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BuildScope:
    build: dict[str, Any]
    asset: dict[str, Any]
    manifest: dict[str, Any]
    source_blocks: list[dict[str, Any]]
    semantic_blocks: list[dict[str, Any]]
    source_quality: dict[str, Any]
    source_scope_repair: bool
