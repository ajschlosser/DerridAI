/* Copyright 2026 Aaron John Schlosser, PhD. */
// Reader pages (Search, Record, Compare) must not have content replaced under a reader. This
// composable follows a data resource through the shared realtime bridge and only reports that
// something newer exists; the page decides when to reload (docs/REALTIME.md).
//
// Only a server `resource.changed` (or a resync, which may hide a gap) counts. The observer
// below fetches nothing over HTTP, and the fallback poll or a window refocus never invalidates
// the query, so neither can raise a false notice.
import { computed, onBeforeUnmount, ref } from "vue";
import { queryClient, useDataQuery } from "../realtime/dataQuery";
import type { DataResource } from "../realtime/resourceKeys";

export function useNewerData(resource: DataResource = "corpus_records") {
  // A mounted observer is what makes the bridge subscribe to this resource's topic.
  useDataQuery(resource, async () => null);
  const changes = ref(0);
  const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
    if (event.type !== "updated" || event.action.type !== "invalidate") return;
    const key = event.query.queryKey;
    if (key[0] === "data" && key[1] === resource) changes.value += 1;
  });
  onBeforeUnmount(unsubscribe);
  return {
    hasNewer: computed(() => changes.value > 0),
    /** Call when the page has loaded current data (or the reader chose to ignore the notice). */
    acknowledge: () => {
      changes.value = 0;
    },
  };
}
