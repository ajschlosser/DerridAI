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

// Follow one server resource that a visible view is watching (a corpus build, a job dialog, a
// translation job). Its realtime events trigger a throttled REST refresh; while the socket is
// unavailable the same refresh runs on a fallback timer instead. The view keeps reading
// authoritative state over REST either way; the socket only says *when* to read.
import { LEGACY_VIEW_POLL_MS, VIEW_FALLBACK_POLL_MS, realtime as defaultRealtime } from "./index";
import type { RealtimeClient } from "./client";
import type { RealtimeEvent } from "./protocol";

export interface FollowOptions {
  /** Realtime topic, e.g. `job:<id>` or `corpus-build:<id>`. */
  topic: string;
  /** Re-read the resource over REST. */
  refresh: () => Promise<unknown> | unknown;
  /**
   * Optional event reducer for views that can apply bounded realtime payloads directly.
   * Return false when the event was fully handled and no authoritative read is needed.
   * Resync and fallback polling still call refresh regardless.
   */
  onEvent?: (event: RealtimeEvent) => boolean | void;
  /** REST poll interval used only while the socket is not live (defaults to followFallbackMs). */
  fallbackMs?: number;
  /** Stop following once this returns true (checked after each refresh). */
  isDone?: () => boolean;
  /** Minimum spacing between event-driven refreshes; bursts collapse into one trailing refresh. */
  minIntervalMs?: number;
  /**
   * Optional slow reconciliation while live, for derived state that changes without an event
   * (for example whether a local model has finished loading). Omit for none.
   */
  reconcileMs?: number;
  /** Read once right away (through the same serialized path as later refreshes). */
  immediate?: boolean;
  client?: RealtimeClient;
}

export function followResource(options: FollowOptions): () => void {
  const client = options.client ?? defaultRealtime;
  const minInterval = options.minIntervalMs ?? 500;
  let stopped = false;
  let running = false;
  let queued = false;
  let lastRun = 0;
  let throttle: ReturnType<typeof setTimeout> | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function run() {
    if (stopped) return;
    if (running) {
      queued = true;
      return;
    }
    running = true;
    lastRun = Date.now();
    try {
      await options.refresh();
    } finally {
      running = false;
    }
    if (options.isDone?.()) {
      stop();
      return;
    }
    if (queued) {
      queued = false;
      request();
    }
  }

  function request() {
    if (stopped || throttle) return;
    const wait = Math.max(0, minInterval - (Date.now() - lastRun));
    throttle = setTimeout(() => {
      throttle = undefined;
      void run();
    }, wait);
  }

  function schedule() {
    if (stopped) return;
    clearTimeout(timer);
    const fallback =
      options.fallbackMs ??
      // Realtime never started (e.g. before bootstrap): keep the view's former cadence.
      (client.status === "idle" ? LEGACY_VIEW_POLL_MS : VIEW_FALLBACK_POLL_MS);
    const delay = client.live ? options.reconcileMs : fallback;
    if (!delay) return;
    timer = setTimeout(async () => {
      await run();
      schedule();
    }, delay);
  }

  const unsubscribe = client.subscribe(options.topic, (event) => {
    if (options.onEvent?.(event) === false) return;
    request();
  });
  const offResync = client.onResync(() => request());
  const offStatus = client.onStatus(() => schedule());

  function stop() {
    if (stopped) return;
    stopped = true;
    clearTimeout(throttle);
    clearTimeout(timer);
    unsubscribe();
    offResync();
    offStatus();
  }

  schedule();
  if (options.immediate) void run();
  return stop;
}
