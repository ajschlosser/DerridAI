/* Copyright 2026 Aaron John Schlosser, PhD. */
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
  } = {},
) {
  return useQuery({
    queryKey: computed(() => dataKey(resource, ...(toValue(options.detail) ?? []))),
    queryFn: fetcher,
    enabled: computed(() => toValue(options.enabled) ?? true),
    // Fallback only: a live socket replaces polling entirely.
    refetchInterval: computed(() => (realtimeFallback.value ? FALLBACK_POLL_MS : false)),
  } as UseQueryOptions<T>);
}
