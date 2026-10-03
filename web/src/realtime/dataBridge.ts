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

// The one bridge between the realtime socket and the server-state cache (TanStack Query).
// The socket says *that* data changed; the cache refetches it over REST/GraphQL. Pages never
// subscribe or poll themselves: they call useDataQuery, and this module follows exactly the
// resources that currently have a mounted observer.
import type { QueryClient } from "@tanstack/vue-query";
import type { RealtimeClient } from "./client";
import { dataTopic, isDataResource, type DataResource } from "./resourceKeys";

export function startDataBridge(client: RealtimeClient, queryClient: QueryClient): () => void {
  const cache = queryClient.getQueryCache();
  const subscriptions = new Map<DataResource, () => void>();

  function observed(): Set<DataResource> {
    const resources = new Set<DataResource>();
    for (const query of cache.findAll({ queryKey: ["data"] })) {
      const resource = query.queryKey[1];
      if (isDataResource(resource) && query.getObserversCount() > 0) resources.add(resource);
    }
    return resources;
  }

  function reconcile() {
    const wanted = observed();
    for (const resource of wanted) {
      if (subscriptions.has(resource)) continue;
      subscriptions.set(
        resource,
        client.subscribe(dataTopic(resource), (event) => {
          if (event.type !== "resource.changed") return;
          void queryClient.invalidateQueries({ queryKey: ["data", resource] });
        }),
      );
    }
    for (const [resource, unsubscribe] of subscriptions) {
      if (wanted.has(resource)) continue;
      unsubscribe();
      subscriptions.delete(resource);
    }
  }

  const stopCache = cache.subscribe((event) => {
    if (event.type === "observerAdded" || event.type === "observerRemoved") reconcile();
  });
  // A gap in the stream (reconnect, overflow) means any cached resource may be stale.
  const stopResync = client.onResync(() => {
    void queryClient.invalidateQueries({ queryKey: ["data"] });
  });
  // Logout, expiry and account switches stop the client; never carry one user's data to the next.
  const stopStatus = client.onStatus((status) => {
    if (status === "idle") queryClient.clear();
  });

  reconcile();
  return () => {
    stopCache();
    stopResync();
    stopStatus();
    for (const unsubscribe of subscriptions.values()) unsubscribe();
    subscriptions.clear();
  };
}
