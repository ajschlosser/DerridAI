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

let tabScrollPreservationWired = false;
export function wireTabScrollPreservation() {
  if (tabScrollPreservationWired) return;
  tabScrollPreservationWired = true;
  const selector = [
    '[role="tab"]',
    ".view-tab",
    ".db-browser-tab",
    ".search-mode-tabs button",
    ".dashboard-search-tabs button",
    ".annotation-tabs button",
    ".annotations-tabs button",
    ".record-view-tabs button",
    ".compare-tabs button",
    ".config-tabs button",
  ].join(",");
  const arm = (target: Element | null) => {
    if (!target) return;
    const top = window.scrollY,
      left = window.scrollX,
      main = document.querySelector("#main");
    let cancelled = false,
      quietTimer: ReturnType<typeof setTimeout> | null = null,
      stopTimer: ReturnType<typeof setTimeout> | null = null,
      observer: MutationObserver | null = null;
    const restore = () => {
      if (cancelled) return;
      if (Math.abs(window.scrollY - top) > 1 || Math.abs(window.scrollX - left) > 1)
        window.scrollTo({ top, left, behavior: "auto" });
    };
    const stop = () => {
      observer?.disconnect();
      if (quietTimer) clearTimeout(quietTimer);
      if (stopTimer) clearTimeout(stopTimer);
      window.removeEventListener("wheel", cancel);
      window.removeEventListener("touchmove", cancel);
    };
    const cancel = () => {
      cancelled = true;
      stop();
    };
    observer = main
      ? new MutationObserver(() => {
          restore();
          if (quietTimer) clearTimeout(quietTimer);
          quietTimer = setTimeout(stop, 140);
        })
      : null;
    observer?.observe(main as Node, { childList: true, subtree: true });
    window.addEventListener("wheel", cancel, { passive: true, once: true });
    window.addEventListener("touchmove", cancel, { passive: true, once: true });
    requestAnimationFrame(restore);
    stopTimer = setTimeout(stop, 1200);
  };
  document.addEventListener(
    "pointerdown",
    (event) => {
      const target = event.target instanceof Element ? event.target.closest(selector) : null;
      if (target) arm(target);
    },
    true,
  );
  document.addEventListener(
    "keydown",
    (event) => {
      if (!["Enter", " "].includes(event.key)) return;
      const target = event.target instanceof Element ? event.target.closest(selector) : null;
      if (target) arm(target);
    },
    true,
  );
}
