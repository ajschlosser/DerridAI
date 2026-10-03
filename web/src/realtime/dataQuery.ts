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

// The app's server-state cache and the composable every page uses to read server data. Realtime
// invalidation (dataBridge) is the only thing that refreshes it while the socket is live; REST
// polling runs here only while the socket is unavailable (docs/REALTIME.md), and nothing else
// may poll.
import { computed, type MaybeRefOrGetter, toValue } from "vue";
import { QueryClient, useQuery, type UseQueryOptions } from "@tanstack/vue-query";
import { realtime, realtimeFallback, FALLBACK_POLL_MS } from "./index";
import { startDataBridge } from "./dataBridge";
import { dataKey, type DataResource } from "./resourceKeys";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Realtime invalidation keeps live data fresh; this only bounds how long data is trusted
      // without it (window refocus, remount, socket down).
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  },
});

startDataBridge(realtime, queryClient);

export function useDataQuery<T>(
  resource: DataResource,
  fetcher: () => Promise<T>,
  options: {
    /** Extra key parts (ids, filters); refetch follows them when reactive. */
    detail?: MaybeRefOrGetter<unknown[]>;
    enabled?: MaybeRefOrGetter<boolean>;
    /** Override the cache's normal freshness window for data that must be revalidated immediately. */
    staleTime?: MaybeRefOrGetter<number>;
    /** Override the cache's normal mount-freshness policy for audit surfaces that must revalidate. */
    refetchOnMount?: MaybeRefOrGetter<boolean | "always">;
  } = {},
) {
  return useQuery({
    queryKey: computed(() => dataKey(resource, ...(toValue(options.detail) ?? []))),
    queryFn: fetcher,
    enabled: computed(() => toValue(options.enabled) ?? true),
    ...(options.staleTime === undefined
      ? {}
      : { staleTime: computed(() => toValue(options.staleTime)!) }),
    ...(options.refetchOnMount === undefined
      ? {}
      : { refetchOnMount: computed(() => toValue(options.refetchOnMount)!) }),
    // Fallback only: a live socket replaces polling entirely.
    refetchInterval: computed(() => (realtimeFallback.value ? FALLBACK_POLL_MS : false)),
  } as UseQueryOptions<T>);
}
