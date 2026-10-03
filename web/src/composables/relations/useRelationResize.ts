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
import type { RelationSize } from "../../domain/relations/types";

export interface RelationResizeOptions {
  minWidth?: number;
  maxWidth?: number;
  minHeight?: number;
  maxHeight?: number;
  keyboardStep?: number;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function useRelationResize(options: RelationResizeOptions = {}) {
  const minWidth = options.minWidth ?? 280;
  const maxWidth = options.maxWidth ?? Number.POSITIVE_INFINITY;
  const minHeight = options.minHeight ?? 220;
  const maxHeight = options.maxHeight ?? 900;
  const keyboardStep = options.keyboardStep ?? 32;
  const size = ref<RelationSize | null>(null);
  const resizing = ref(false);

  let pointer:
    | {
        id: number;
        startX: number;
        startY: number;
        origin: RelationSize;
        axis: "horizontal" | "vertical" | "both";
      }
    | undefined;

  function normalize(next: RelationSize): RelationSize {
    return {
      width: clamp(next.width, minWidth, maxWidth),
      height: clamp(next.height, minHeight, maxHeight),
    };
  }

  function setSize(next: RelationSize | null) {
    size.value = next ? normalize(next) : null;
  }

  function begin(
    event: PointerEvent,
    current: RelationSize,
    axis: "horizontal" | "vertical" | "both" = "both",
  ) {
    if (event.button != null && event.button !== 0) return false;
    pointer = {
      id: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: normalize(current),
      axis,
    };
    resizing.value = true;
    (event.currentTarget as Element | null)?.setPointerCapture?.(event.pointerId);
    event.preventDefault();
    event.stopPropagation();
    return true;
  }

  function update(event: PointerEvent) {
    if (!pointer || pointer.id !== event.pointerId) return false;
    const widthDelta = pointer.axis === "vertical" ? 0 : event.clientX - pointer.startX;
    const heightDelta = pointer.axis === "horizontal" ? 0 : event.clientY - pointer.startY;
    size.value = normalize({
      width: pointer.origin.width + widthDelta,
      height: pointer.origin.height + heightDelta,
    });
    event.preventDefault();
    event.stopPropagation();
    return true;
  }

  function end(event?: PointerEvent) {
    if (!pointer) return false;
    if (event && pointer.id === event.pointerId) {
      (event.currentTarget as Element | null)?.releasePointerCapture?.(event.pointerId);
      event.preventDefault();
      event.stopPropagation();
    }
    pointer = undefined;
    resizing.value = false;
    return true;
  }

  function keyboardResize(
    event: KeyboardEvent,
    current: RelationSize,
    axis: "horizontal" | "vertical" | "both" = "both",
  ) {
    const step = event.shiftKey ? keyboardStep * 2 : keyboardStep;
    let width = current.width;
    let height = current.height;
    if ((axis === "horizontal" || axis === "both") && event.key === "ArrowLeft") width -= step;
    else if ((axis === "horizontal" || axis === "both") && event.key === "ArrowRight")
      width += step;
    else if ((axis === "vertical" || axis === "both") && event.key === "ArrowUp") height -= step;
    else if ((axis === "vertical" || axis === "both") && event.key === "ArrowDown") height += step;
    else return false;
    size.value = normalize({ width, height });
    event.preventDefault();
    event.stopPropagation();
    return true;
  }

  function resetSize() {
    size.value = null;
  }

  return { size, resizing, setSize, begin, update, end, keyboardResize, resetSize };
}
