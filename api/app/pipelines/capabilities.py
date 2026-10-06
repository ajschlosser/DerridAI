# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Machine-readable compatibility identity for declarative pipelines.

Pipeline Studio, the API, and native binaries all consume the same code-owned
strategy registry.  This module exposes only compatibility facts: it deliberately
does not duplicate labels, presentation metadata, or pipeline definitions.
"""

from __future__ import annotations

from typing import Any

from .registry import StrategyRegistry, strategy_registry

PIPELINE_CONTRACT_VERSION = 1
MINIMUM_READABLE_PIPELINE_VERSION = 1


def pipeline_contract_identity(
    registry: StrategyRegistry = strategy_registry,
    *,
    application_version: str | None = None,
) -> dict[str, Any]:
    """Return the compatibility identity implemented by this source tree.

    Strategy versions are sorted by stable strategy ID so the same mapping can be
    compared directly across the API catalog, source tests, and compiled binaries.
    """

    if application_version is None:
        from ..config import APP_VERSION

        application_version = APP_VERSION

    return {
        "pipeline_contract_version": PIPELINE_CONTRACT_VERSION,
        "minimum_readable_pipeline_version": MINIMUM_READABLE_PIPELINE_VERSION,
        "application_version": str(application_version),
        "strategies": {
            spec.strategy_id: {"version": spec.version}
            for spec in registry.list()
        },
    }
