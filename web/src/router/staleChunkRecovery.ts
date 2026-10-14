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

function normalizedScriptPath(src: string, base = window.location.origin): string {
  try {
    const url = new URL(src, base);
    return `${url.pathname}${url.search}`;
  } catch {
    return src;
  }
}

export function currentEntryScriptPath(doc: Document = document): string {
  const script = doc.querySelector<HTMLScriptElement>('script[type="module"][src]');
  const src = script?.getAttribute("src") || "";
  return src ? normalizedScriptPath(src, doc.baseURI || window.location.origin) : "";
}

export function entryScriptPathFromHtml(html: string, base = window.location.origin): string {
  const parsed = new DOMParser().parseFromString(html, "text/html");
  const script = parsed.querySelector<HTMLScriptElement>('script[type="module"][src]');
  const src = script?.getAttribute("src") || "";
  return src ? normalizedScriptPath(src, base) : "";
}

/**
 * A failed lazy import is only a deployment-staleness condition when the HTML
 * currently served by nginx references a different entry bundle than the one
 * that booted this tab. A transient network failure should keep the existing
 * route-error UI instead of forcing a reload.
 */
export async function deploymentShellChanged(
  fetcher: typeof fetch = window.fetch.bind(window),
  doc: Document = document,
): Promise<boolean> {
  const currentEntry = currentEntryScriptPath(doc);
  if (!currentEntry) return false;
  try {
    const response = await fetcher("/index.html", {
      cache: "no-store",
      headers: {
        Accept: "text/html",
        "Cache-Control": "no-cache",
      },
    });
    if (!response.ok) return false;
    const nextEntry = entryScriptPathFromHtml(await response.text(), doc.baseURI);
    return Boolean(nextEntry && nextEntry !== currentEntry);
  } catch {
    return false;
  }
}

function recoverOnce(): boolean {
  if (!claimStaleChunkRecovery(window.sessionStorage)) return false;
  window.location.reload();
  return true;
}

let recoveryCheck: Promise<boolean> | null = null;

function recoverIfDeploymentChanged(): Promise<boolean> {
  if (recoveryCheck) return recoveryCheck;
  recoveryCheck = deploymentShellChanged()
    .then((changed) => changed && recoverOnce())
    .finally(() => {
      recoveryCheck = null;
    });
  return recoveryCheck;
}

/**
 * Vite emits vite:preloadError when a lazy chunk cannot be loaded. Do not
 * assume every such failure means a deployment changed: first compare the
 * current tab's entry bundle with the no-cache HTML shell served by nginx.
 *
 * The router error hook covers route imports; the Vite event also covers other
 * lazy imports. Both share one in-flight deployment check and one guarded
 * recovery reload.
 */
export function installStaleChunkRecovery(router: Router): () => void {
  const onPreloadError = (event: Event) => {
    const payload = (event as VitePreloadErrorEvent).payload;
    if (!payload || isLikelyStaleModuleError(payload)) void recoverIfDeploymentChanged();
  };
  window.addEventListener("vite:preloadError", onPreloadError);

  const stopRouterError = router.onError((error) => {
    if (isLikelyStaleModuleError(error)) void recoverIfDeploymentChanged();
  });

  return () => {
    window.removeEventListener("vite:preloadError", onPreloadError);
    stopRouterError();
  };
}
