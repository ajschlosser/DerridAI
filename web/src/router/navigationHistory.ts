/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, shallowRef } from "vue";
import type { RouteLocationNormalized, Router } from "vue-router";

// The router (and the browser history it wraps) is the only navigation history. Vue Router records the previous and next
// entry in `history.state`; this module reads that and remembers a title for recently visited locations so Back/Forward
// controls can say where they lead.

export type HistoryEntryTitle = { key: string; fallback: string };
type HistoryState = { back?: string | null; forward?: string | null } | null;

/** Bounds the title record; the browser history itself is unbounded but only nearby entries are ever looked up. */
export const MAX_REMEMBERED_TITLES = 100;

export function createNavigationHistory(
  router: Router,
  readHistoryState: () => HistoryState = () => window.history.state,
) {
  const titles = new Map<string, HistoryEntryTitle>();
  const backPath = shallowRef<string | null>(null);
  const forwardPath = shallowRef<string | null>(null);
  // Bumped when a title is recorded so label lookups recompute.
  const titleVersion = shallowRef(0);

  function remember(to: RouteLocationNormalized) {
    const key = String(to.meta.titleKey || "");
    const fallback = String(to.meta.titleFallback || "");
    if (!key && !fallback) return;
    titles.delete(to.fullPath);
    titles.set(to.fullPath, { key, fallback });
    while (titles.size > MAX_REMEMBERED_TITLES) {
      const oldest = titles.keys().next().value;
      if (oldest === undefined) break;
      titles.delete(oldest);
    }
    titleVersion.value += 1;
  }

  function refresh() {
    let state: HistoryState = null;
    try {
      state = readHistoryState();
    } catch {
      // History state can be unreadable (sandboxed frames); treat as no history rather than failing navigation.
    }
    backPath.value = typeof state?.back === "string" ? state.back : null;
    forwardPath.value = typeof state?.forward === "string" ? state.forward : null;
  }

  const stopListening = router.afterEach((to, _from, failure) => {
    if (failure) return;
    remember(to);
    refresh();
  });

  function titleFor(path: string | null): HistoryEntryTitle | null {
    void titleVersion.value;
    return path ? (titles.get(path) ?? null) : null;
  }

  return {
    canGoBack: computed(() => backPath.value !== null),
    canGoForward: computed(() => forwardPath.value !== null),
    backTitle: computed(() => titleFor(backPath.value)),
    forwardTitle: computed(() => titleFor(forwardPath.value)),
    back: () => router.back(),
    forward: () => router.forward(),
    refresh,
    dispose: stopListening,
  };
}
