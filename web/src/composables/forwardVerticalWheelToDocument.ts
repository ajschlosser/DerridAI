/* Copyright 2026 Aaron John Schlosser, PhD. */

const VERTICAL_SCROLLPORTS = new Set(["auto", "scroll", "overlay"]);

function canScrollVertically(node: HTMLElement, deltaY: number): boolean {
  if (node.scrollHeight - node.clientHeight <= 1) return false;
  if (deltaY > 0) return node.scrollTop + node.clientHeight < node.scrollHeight - 1;
  return node.scrollTop > 1;
}

/**
 * Chromium treats overflow:auto nodes as wheel targets even when they cannot
 * scroll further on that axis, so the document never moves. If every scrollport
 * in the event path is exhausted, apply leftover deltaY to the page scroller.
 */
export function forwardVerticalWheelToDocument(event: WheelEvent): void {
  if (!event.deltaY || event.defaultPrevented) return;
  let trapped = false;
  for (const node of event.composedPath()) {
    if (!(node instanceof HTMLElement)) continue;
    if (node === document.documentElement || node === document.body) break;
    const overflowY = getComputedStyle(node).overflowY;
    if (!VERTICAL_SCROLLPORTS.has(overflowY)) continue;
    if (canScrollVertically(node, event.deltaY)) return;
    trapped = true;
    break;
  }
  if (!trapped) return;
  const root = document.scrollingElement || document.documentElement;
  root.scrollTop += event.deltaY;
}
