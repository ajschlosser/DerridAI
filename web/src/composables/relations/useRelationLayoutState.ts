/* Copyright 2026 Aaron John Schlosser, PhD. */
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
