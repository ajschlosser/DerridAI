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

import { computed, ref, watch, type Ref } from "vue";
import {
  metadataMemoryApi,
  type MetadataMemoryListFilters,
  type MetadataMemoryPayload,
} from "../api/metadataMemory";
import { useDataQuery } from "../realtime/dataQuery";
import { useAuthStore } from "../stores/auth";

/**
 * Owns the server-state semantics for Metadata Memory.
 *
 * The audit page must not turn a failed read into a believable empty result.  A successful
 * payload is retained across same-query refreshes; a changed query can explicitly clear it.
 * Empty cached pages are never presented as current while a mandatory revalidation is running.
 */
export function useMetadataMemoryData(applied: Ref<MetadataMemoryListFilters>) {
  const auth = useAuthStore();
  const scope = computed(() => [
    auth.user?.id ?? "anonymous",
    auth.user?.role ?? "",
    [...(auth.user?.capabilities ?? [])].sort(),
  ]);
  const identity = computed(() => JSON.stringify([scope.value, applied.value]));
  const payload = ref<MetadataMemoryPayload | null>(null);
  const serviceError = ref("");
  const accessRevoked = ref(false);

  const query = useDataQuery(
    "metadata_exemplars",
    () => metadataMemoryApi.list({ ...applied.value }),
    {
      detail: () => ["workspace", applied.value, ...scope.value],
      staleTime: 0,
      refetchOnMount: "always",
    },
  );

  // Retained content belongs only to this exact filter and authorization scope.
  watch(identity, clearForNewQuery, { flush: "sync" });

  const loading = computed(() => query.isFetching.value);
  const transportError = computed(() => {
    const failure = query.error.value;
    if (!failure) return "";
    return failure instanceof Error ? failure.message : String(failure);
  });
  const readError = computed(() => serviceError.value || transportError.value);
  const ready = computed(() => Boolean(payload.value));
  const waiting = computed(() => !ready.value && !readError.value);
  const refreshing = computed(() => loading.value && ready.value);

  watch(
    () => [query.data.value, query.error.value, query.isFetching.value] as const,
    ([data, error, fetching]) => {
      const denied = Boolean(
        error &&
          typeof error === "object" &&
          "status" in error &&
          [401, 403].includes(Number(error.status)),
      );
      if (denied) {
        accessRevoked.value = true;
        payload.value = null;
        serviceError.value = "";
        return;
      }
      if (fetching) {
        // Reuse a populated cache as stale-but-useful content while it revalidates.  Do not reuse
        // a cached zero-row result: that is the failure mode that made new precedents look absent.
        if (!accessRevoked.value && !payload.value && data?.available && data.items.length > 0)
          payload.value = data;
        return;
      }
      if (error || !data) return;
      if (!data.available) {
        serviceError.value = String(data.error || "");
        return;
      }
      serviceError.value = "";
      accessRevoked.value = false;
      payload.value = data;
    },
    { immediate: true },
  );

  function clearForNewQuery() {
    payload.value = null;
    serviceError.value = "";
  }

  async function refetch() {
    await query.refetch();
  }

  return {
    payload,
    loading,
    ready,
    waiting,
    refreshing,
    readError,
    clearForNewQuery,
    refetch,
  };
}
