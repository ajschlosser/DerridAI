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

import type { Router } from "vue-router";

const RECOVERY_WINDOW_MS = 30_000;
const RECOVERY_KEY = "derridai.ui.staleChunkRecovery";

interface VitePreloadErrorEvent extends Event {
  payload?: unknown;
}

function buildIdentity() {
  return String(__APP_GIT_COMMIT__ || __APP_VERSION__ || "unknown");
}

/** Firefox, Chromium, Safari, and older bundlers use different module-load wording. */
export function isLikelyStaleModuleError(error: unknown): boolean {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === "string"
        ? error
        : String((error as { message?: unknown } | null)?.message || error || "");
  return [
    "Failed to fetch dynamically imported module",
    "error loading dynamically imported module",
    "Importing a module script failed",
    "Unable to preload CSS",
    "Loading chunk",
    "ChunkLoadError",
  ].some((fragment) => message.includes(fragment));
}

/**
 * Claim the single automatic reload allowed for this build in a short window.
 * sessionStorage survives a reload but not a new browser session, preventing a
 * stale proxy/browser from turning a missing chunk into an infinite reload loop.
 */
export function claimStaleChunkRecovery(
  storage: Pick<Storage, "getItem" | "setItem">,
  now = Date.now(),
  identity = buildIdentity(),
): boolean {
  try {
    const previous = storage.getItem(RECOVERY_KEY);
    if (previous) {
      const [previousIdentity, timestamp] = previous.split("|", 2);
      if (
        previousIdentity === identity &&
        Number.isFinite(Number(timestamp)) &&
        now - Number(timestamp) < RECOVERY_WINDOW_MS
      ) {
        return false;
      }
    }
    storage.setItem(RECOVERY_KEY, `${identity}|${now}`);
    return true;
  } catch {
    // Private/restricted storage should not disable recovery for the current page.
    return true;
  }
}

function recoverOnce(): boolean {
  if (!claimStaleChunkRecovery(window.sessionStorage)) return false;
  window.location.reload();
  return true;
}

/**
 * Vite emits vite:preloadError when a lazy route chunk referenced by the
 * currently running bundle is gone. This commonly happens when a user keeps a
 * tab open while Docker replaces the frontend image. Reload once so nginx can
 * serve the current no-cache HTML shell and its matching chunk graph.
 *
 * The router error hook is a fallback for browsers that surface the failed
 * dynamic import without the Vite preload event.
 */
export function installStaleChunkRecovery(router: Router): () => void {
  const onPreloadError = (event: Event) => {
    const preload = event as VitePreloadErrorEvent;
    if (recoverOnce()) event.preventDefault();
    else if (preload.payload) console.error("Route asset reload failed", preload.payload);
  };
  window.addEventListener("vite:preloadError", onPreloadError);

  const stopRouterError = router.onError((error) => {
    if (isLikelyStaleModuleError(error)) recoverOnce();
  });

  return () => {
    window.removeEventListener("vite:preloadError", onPreloadError);
    stopRouterError();
  };
}
