/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { shallowRef } from "vue";
import type { RelationPoint } from "../../domain/relations/types";

/**
 * Presentation-only manual position overrides.
 *
 * The map is replaced on every write so Vue consumers react predictably
 * without making graph-domain objects reactive or mutable.
 */
export function useRelationLayoutState() {
  const positionOverrides = shallowRef(new Map<string, RelationPoint>());

  function setPosition(id: string, point: RelationPoint) {
    const next = new Map(positionOverrides.value);
    next.set(id, { ...point });
    positionOverrides.value = next;
  }

  function clearPosition(id: string) {
    if (!positionOverrides.value.has(id)) return;
    const next = new Map(positionOverrides.value);
    next.delete(id);
    positionOverrides.value = next;
  }

  function clearPositions() {
    positionOverrides.value = new Map();
  }

  function positionFor(id: string, fallback: RelationPoint): RelationPoint {
    return positionOverrides.value.get(id) ?? fallback;
  }

  return {
    positionOverrides,
    setPosition,
    clearPosition,
    clearPositions,
    positionFor,
  };
}
