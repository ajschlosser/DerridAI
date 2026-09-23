// Copyright 2026 Aaron John Schlosser, PhD.
import { onBeforeUnmount, ref, type Ref } from "vue";

/**
 * The width of a resizable pane, with the pointer and keyboard controls a window splitter needs.
 *
 * WCAG 2.5.7 asks for a single-pointer alternative to dragging, so the same size can be changed with
 * the arrow keys (Shift for a larger step), Home and End, and a double click resets it. The size is
 * remembered per browser. `edge` says which side of the separator the pane is on: "start" is the
 * pane before it (the queue), "end" the pane after it (the inspector). Directions follow the
 * container's writing direction, so a right-to-left layout resizes the way it looks.
 */
export interface SplitterOptions {
  /** localStorage key that remembers the size. */
  key: string;
  min: number;
  max: number;
  initial: number;
  edge: "start" | "end";
  /** The axis being resized. Width is the default for existing splitters. */
  axis?: "horizontal" | "vertical";
  /** The element whose edges the size is measured from. */
  container: () => HTMLElement | null;
  step?: number;
}

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

function remembered(key: string, fallback: number): number {
  try {
    const stored = Number(localStorage.getItem(key));
    return Number.isFinite(stored) && stored > 0 ? stored : fallback;
  } catch {
    return fallback;
  }
}

export function useSplitter(options: SplitterOptions) {
  const { min, max, edge } = options;
  const axis = options.axis ?? "horizontal";
  const step = options.step ?? 16;
  const size: Ref<number> = ref(clamp(remembered(options.key, options.initial), min, max));
  const dragging = ref(false);

  function commit(next: number) {
    size.value = Math.round(clamp(next, min, max));
    try {
      localStorage.setItem(options.key, String(size.value));
    } catch {
      // Not being able to remember a width is not worth an error.
    }
  }

  const isRtl = (container: HTMLElement) => getComputedStyle(container).direction === "rtl";
  /** True when the pane sits on the left of the separator, whatever the writing direction. */
  const paneIsOnLeft = (container: HTMLElement) => (edge === "start") !== isRtl(container);

  function fromPointer(event: PointerEvent) {
    const container = options.container();
    if (!container) return;
    const box = container.getBoundingClientRect();
    if (axis === "vertical") {
      // A top pane uses the distance from the container's top edge; a bottom
      // pane uses the distance from its bottom edge.
      commit(edge === "start" ? event.clientY - box.top : box.bottom - event.clientY);
      return;
    }
    // The pane's width is the distance from its own outer edge to the pointer.
    commit(paneIsOnLeft(container) ? event.clientX - box.left : box.right - event.clientX);
  }

  function stop() {
    dragging.value = false;
    window.removeEventListener("pointermove", fromPointer);
    window.removeEventListener("pointerup", stop);
    window.removeEventListener("pointercancel", stop);
    document.body.classList.remove("splitter-dragging");
    document.body.classList.remove("splitter-dragging-vertical");
  }

  function onPointerDown(event: PointerEvent) {
    if (event.button > 0) return; // only the primary button drags
    event.preventDefault();
    dragging.value = true;
    (event.currentTarget as HTMLElement | null)?.setPointerCapture?.(event.pointerId);
    document.body.classList.add("splitter-dragging");
    if (axis === "vertical") document.body.classList.add("splitter-dragging-vertical");
    window.addEventListener("pointermove", fromPointer);
    window.addEventListener("pointerup", stop);
    window.addEventListener("pointercancel", stop);
  }

  function onKeydown(event: KeyboardEvent) {
    const container = options.container();
    if (!container) return;
    const amount = event.shiftKey ? step * 4 : step;
    if (axis === "vertical") {
      const down = edge === "start" ? 1 : -1;
      let next = size.value;
      if (event.key === "ArrowDown") next += amount * down;
      else if (event.key === "ArrowUp") next -= amount * down;
      else if (event.key === "Home") next = min;
      else if (event.key === "End") next = max;
      else return;
      event.preventDefault();
      commit(next);
      return;
    }
    // Moving the separator to the right grows a pane on its left and shrinks one on its right.
    const right = paneIsOnLeft(container) ? 1 : -1;
    let next = size.value;
    if (event.key === "ArrowRight") next += amount * right;
    else if (event.key === "ArrowLeft") next -= amount * right;
    else if (event.key === "Home") next = min;
    else if (event.key === "End") next = max;
    else return;
    event.preventDefault();
    commit(next);
  }

  function reset() {
    commit(options.initial);
  }

  onBeforeUnmount(stop);

  return {
    size,
    dragging,
    onPointerDown,
    onKeydown,
    reset,
    /** Attributes for the separator element. */
    aria: () => ({ "aria-valuemin": min, "aria-valuemax": max, "aria-valuenow": size.value }),
  };
}
