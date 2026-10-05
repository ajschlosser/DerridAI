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

import { onBeforeUnmount, ref, watch } from "vue";
import { researchThreadsApi } from "../../api/researchThreads";
import { useAuthStore } from "../../stores/auth";

const AUTO_IMPORT_PAUSE_MS = 750;

/** Incremental migration is independent of the authoritative Library reads. */
export function useLegacyThreadImport() {
  const auth = useAuthStore();
  const busy = ref(false);
  const error = ref("");
  const hasMore = ref(true);
  const refreshKey = ref(0);
  let offset = 0;
  let request = 0;
  let scheduled: number | undefined;
  let disposed = false;

  function cancelScheduled() {
    if (scheduled !== undefined) window.clearTimeout(scheduled);
    scheduled = undefined;
  }

  function scheduleNextBatch() {
    cancelScheduled();
    if (disposed || busy.value || error.value || !hasMore.value || !auth.can("rag.run")) return;
    // Legacy response migration is maintenance work, not a prerequisite for
    // using the Library. Yield between batches so search, navigation, and
    // Research rendering remain responsive while a large history is imported.
    scheduled = window.setTimeout(() => {
      scheduled = undefined;
      void retry();
    }, AUTO_IMPORT_PAUSE_MS);
  }

  async function retry() {
    if (busy.value || !auth.can("rag.run")) return;
    cancelScheduled();
    const current = ++request;
    busy.value = true;
    error.value = "";
    try {
      const result = await researchThreadsApi.importLegacy(offset);
      if (current !== request) return;
      offset = result.next_offset;
      hasMore.value = result.has_more;
      ++refreshKey.value;
    } catch (reason) {
      if (current === request)
        error.value = reason instanceof Error ? reason.message : String(reason);
    } finally {
      if (current === request) {
        busy.value = false;
        if (hasMore.value && !error.value) scheduleNextBatch();
      }
    }
  }
  watch(
    () => [auth.user?.id, auth.user?.role, auth.can("rag.run")],
    () => {
      ++request;
      cancelScheduled();
      offset = 0;
      busy.value = false;
      error.value = "";
      hasMore.value = true;
      if (auth.can("rag.run")) scheduleNextBatch();
    },
    { immediate: true },
  );
  onBeforeUnmount(() => {
    disposed = true;
    ++request;
    cancelScheduled();
  });
  return { busy, error, hasMore, refreshKey, retry };
}
