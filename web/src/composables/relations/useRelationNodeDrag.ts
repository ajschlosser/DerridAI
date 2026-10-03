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

import { ref } from "vue";
import { moveRelationPoint } from "../../domain/relations/geometry";
import type { RelationPoint } from "../../domain/relations/types";

export interface RelationNodeDragOptions {
  getZoom: () => number;
  onMove: (point: RelationPoint) => void;
  threshold?: number;
  nudgeStep?: number;
}

export function useRelationNodeDrag(options: RelationNodeDragOptions) {
  const dragging = ref(false);
  const moved = ref(false);
  const threshold = options.threshold ?? 4;
  const nudgeStep = options.nudgeStep ?? 8;

  let pointer:
    | {
        id: number;
        start: RelationPoint;
        origin: RelationPoint;
        zoom: number;
      }
    | undefined;

  function begin(event: PointerEvent, point: RelationPoint) {
    if (event.button != null && event.button !== 0) return false;
    pointer = {
      id: event.pointerId,
      start: { x: event.clientX, y: event.clientY },
      origin: { ...point },
      zoom: options.getZoom(),
    };
    moved.value = false;
    (event.currentTarget as Element | null)?.setPointerCapture?.(event.pointerId);
    return true;
  }

  function update(event: PointerEvent) {
    if (!pointer || pointer.id !== event.pointerId) return false;
    const delta = {
      x: event.clientX - pointer.start.x,
      y: event.clientY - pointer.start.y,
    };
    if (!moved.value && Math.hypot(delta.x, delta.y) < threshold) return false;
    moved.value = true;
    dragging.value = true;
    options.onMove(moveRelationPoint(pointer.origin, delta, pointer.zoom));
    return true;
  }

  function end(event?: PointerEvent) {
    if (!pointer) return false;
    const didMove = moved.value;
    if (event && pointer.id === event.pointerId) {
      (event.currentTarget as Element | null)?.releasePointerCapture?.(event.pointerId);
    }
    pointer = undefined;
    dragging.value = false;
    return didMove;
  }

  function consumeClick(event: MouseEvent) {
    if (!moved.value) return false;
    event.preventDefault();
    event.stopPropagation();
    moved.value = false;
    return true;
  }

  function nudge(event: KeyboardEvent, point: RelationPoint) {
    if (!event.altKey) return false;
    const step = event.shiftKey ? nudgeStep * 3 : nudgeStep;
    let delta: RelationPoint | undefined;
    if (event.key === "ArrowLeft") delta = { x: -step, y: 0 };
    else if (event.key === "ArrowRight") delta = { x: step, y: 0 };
    else if (event.key === "ArrowUp") delta = { x: 0, y: -step };
    else if (event.key === "ArrowDown") delta = { x: 0, y: step };
    if (!delta) return false;
    options.onMove({ x: point.x + delta.x, y: point.y + delta.y });
    event.preventDefault();
    event.stopPropagation();
    return true;
  }

  return { dragging, moved, begin, update, end, consumeClick, nudge };
}
