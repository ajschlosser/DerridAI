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
