/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref, type Ref } from "vue";
import {
  clampRelationZoom,
  fitRelationBounds,
  panRelationViewport,
  zoomRelationViewportAt,
} from "../../domain/relations/geometry";
import type {
  RelationBounds,
  RelationPoint,
  RelationSize,
  RelationViewportState,
} from "../../domain/relations/types";

export interface RelationViewportOptions {
  minZoom?: number;
  maxZoom?: number;
  initialZoom?: number;
  panStep?: number;
  dragThreshold?: number;
}

export function useRelationViewport(options: RelationViewportOptions = {}) {
  const minZoom = options.minZoom ?? 0.45;
  const maxZoom = options.maxZoom ?? 6;
  const panStep = options.panStep ?? 48;
  const dragThreshold = options.dragThreshold ?? 4;
  const pan = ref<RelationPoint>({ x: 0, y: 0 });
  const zoom = ref(clampRelationZoom(options.initialZoom ?? 1, minZoom, maxZoom));
  const panning = ref(false);

  let pointer:
    | {
        id: number;
        start: RelationPoint;
        origin: RelationPoint;
        active: boolean;
      }
    | undefined;

  const state = computed<RelationViewportState>(() => ({
    pan: pan.value,
    zoom: zoom.value,
  }));

  function setState(next: RelationViewportState) {
    pan.value = { ...next.pan };
    zoom.value = clampRelationZoom(next.zoom, minZoom, maxZoom);
  }

  function setZoom(nextZoom: number, anchor?: RelationPoint) {
    if (!anchor) {
      zoom.value = clampRelationZoom(nextZoom, minZoom, maxZoom);
      return;
    }
    setState(zoomRelationViewportAt(state.value, nextZoom, anchor, minZoom, maxZoom));
  }

  function zoomBy(factor: number, anchor?: RelationPoint) {
    setZoom(zoom.value * factor, anchor);
  }

  function centerOn(point: RelationPoint, viewportSize: RelationSize, nextZoom = zoom.value) {
    const normalized = clampRelationZoom(nextZoom, minZoom, maxZoom);
    zoom.value = normalized;
    pan.value = {
      x: viewportSize.width / 2 - point.x * normalized,
      y: viewportSize.height / 2 - point.y * normalized,
    };
  }

  function fit(bounds: RelationBounds, viewportSize: RelationSize, padding = 32) {
    setState(
      fitRelationBounds(bounds, viewportSize, {
        padding,
        minZoom,
        maxZoom,
      }),
    );
  }

  function beginPan(event: PointerEvent) {
    if (event.button != null && event.button !== 0) return false;
    pointer = {
      id: event.pointerId,
      start: { x: event.clientX, y: event.clientY },
      origin: { ...pan.value },
      active: false,
    };
    (event.currentTarget as Element | null)?.setPointerCapture?.(event.pointerId);
    return true;
  }

  function updatePan(event: PointerEvent) {
    if (!pointer || pointer.id !== event.pointerId) return false;
    const delta = {
      x: event.clientX - pointer.start.x,
      y: event.clientY - pointer.start.y,
    };
    if (!pointer.active && Math.hypot(delta.x, delta.y) < dragThreshold) return false;
    pointer.active = true;
    panning.value = true;
    pan.value = panRelationViewport(pointer.origin, delta);
    return true;
  }

  function endPan(event?: PointerEvent) {
    if (!pointer) return false;
    const moved = pointer.active;
    if (event && pointer.id === event.pointerId) {
      (event.currentTarget as Element | null)?.releasePointerCapture?.(event.pointerId);
    }
    pointer = undefined;
    panning.value = false;
    return moved;
  }

  function panBy(delta: RelationPoint) {
    pan.value = panRelationViewport(pan.value, delta);
  }

  function handleViewportKeydown(event: KeyboardEvent) {
    const step = event.shiftKey ? panStep * 2 : panStep;
    if (event.key === "ArrowLeft") panBy({ x: step, y: 0 });
    else if (event.key === "ArrowRight") panBy({ x: -step, y: 0 });
    else if (event.key === "ArrowUp") panBy({ x: 0, y: step });
    else if (event.key === "ArrowDown") panBy({ x: 0, y: -step });
    else if (event.key === "+" || event.key === "=") zoomBy(1.15);
    else if (event.key === "-" || event.key === "_") zoomBy(1 / 1.15);
    else return false;
    event.preventDefault();
    return true;
  }

  return {
    pan,
    zoom,
    state,
    panning,
    setState,
    setZoom,
    zoomBy,
    centerOn,
    fit,
    beginPan,
    updatePan,
    endPan,
    panBy,
    handleViewportKeydown,
  };
}
