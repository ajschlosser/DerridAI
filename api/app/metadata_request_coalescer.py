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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Bounded, process-local sharing of identical in-flight metadata calls only."""

from __future__ import annotations

import copy
import threading
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any


class MetadataRequestCoalescer:
    def __init__(self, capacity: int = 64) -> None:
        if capacity < 1:
            raise ValueError("Metadata coalescing capacity must be positive")
        self.capacity = capacity
        self._lock = threading.Lock()
        self._pending: dict[str, Future[tuple[dict[str, Any], bool]]] = {}

    def run(
        self, key: str, operation: Callable[[], dict[str, Any]], *,
        reusable: Callable[[dict[str, Any]], bool], timeout: float,
    ) -> tuple[dict[str, Any], bool]:
        with self._lock:
            future = self._pending.get(key)
            leader = future is None
            if leader and len(self._pending) < self.capacity:
                future = Future()
                self._pending[key] = future
        if future is None:
            # Capacity limits bookkeeping, never provider admission or domain policy.
            return operation(), False
        if not leader:
            value, can_reuse = future.result(timeout=timeout)
            return (copy.deepcopy(value), True) if can_reuse else (operation(), False)
        try:
            value = operation()
            future.set_result((copy.deepcopy(value), reusable(value)))
            return value, False
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                del self._pending[key]
