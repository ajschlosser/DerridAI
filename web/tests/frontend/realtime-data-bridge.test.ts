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

import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryObserver } from "@tanstack/vue-query";
import { RealtimeClient, type SocketLike } from "../../src/realtime/client";
import { startDataBridge } from "../../src/realtime/dataBridge";
import { dataKey } from "../../src/realtime/resourceKeys";

class FakeSocket implements SocketLike {
  readyState = 1;
  sent: string[] = [];
  onopen: SocketLike["onopen"] = null;
  onmessage: SocketLike["onmessage"] = null;
  onclose: SocketLike["onclose"] = null;
  onerror: SocketLike["onerror"] = null;
  send(data: string) {
    this.sent.push(data);
  }
  close() {}
  push(frame: unknown) {
    this.onmessage?.({ data: JSON.stringify(frame) });
  }
}

function setup() {
  const socket = new FakeSocket();
  const client = new RealtimeClient({ createSocket: () => socket });
  const queryClient = new QueryClient();
  client.start();
  socket.push({
    type: "connection.ready",
    payload: {
      protocol_version: 1,
      connection_id: "c",
      last_event_id: 0,
      heartbeat_seconds: 20,
      idle_timeout_seconds: 60,
    },
  });
  const stop = startDataBridge(client, queryClient);
  return { socket, client, queryClient, stop };
}

function changed(resource: string, id: number) {
  return {
    type: "resource.changed",
    event_id: id,
    resource_type: "data",
    resource_id: resource,
    revision: id,
    timestamp: "2026-09-30T00:00:00Z",
    payload: { resource },
  };
}

function observe(queryClient: QueryClient, resource: "users" | "roles") {
  const fetcher = vi.fn(async () => [] as unknown[]);
  const observer = new QueryObserver(queryClient, {
    queryKey: dataKey(resource),
    queryFn: fetcher,
  });
  const unsubscribe = observer.subscribe(() => {});
  return { fetcher, unsubscribe };
}

describe("data bridge", () => {
  it("subscribes only to resources with a mounted observer and refetches them on resource.changed", async () => {
    const { socket, queryClient } = setup();
    const { fetcher } = observe(queryClient, "users");
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    expect(socket.sent.map((m) => JSON.parse(m))).toContainEqual({
      type: "subscribe",
      topics: ["data:users"],
    });
    expect(socket.sent.join()).not.toContain("data:roles");
    fetcher.mockClear();
    socket.push(changed("users", 1));
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  });

  it("does not refetch unrelated resources", async () => {
    const { socket, queryClient } = setup();
    const users = observe(queryClient, "users");
    const roles = observe(queryClient, "roles");
    await vi.waitFor(() => expect(users.fetcher).toHaveBeenCalledTimes(1));
    await vi.waitFor(() => expect(roles.fetcher).toHaveBeenCalledTimes(1));
    users.fetcher.mockClear();
    roles.fetcher.mockClear();
    socket.push(changed("roles", 2));
    await vi.waitFor(() => expect(roles.fetcher).toHaveBeenCalledTimes(1));
    expect(users.fetcher).not.toHaveBeenCalled();
  });

  it("unsubscribes when the last observer goes away", async () => {
    const { socket, queryClient } = setup();
    const { unsubscribe } = observe(queryClient, "users");
    unsubscribe();
    expect(socket.sent.map((m) => JSON.parse(m))).toContainEqual({
      type: "unsubscribe",
      topics: ["data:users"],
    });
  });

  it("invalidates every followed resource when the stream has a gap", async () => {
    const { socket, queryClient } = setup();
    const { fetcher } = observe(queryClient, "users");
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    fetcher.mockClear();
    socket.push({
      type: "connection.resync_required",
      payload: { reason: "overflow", last_event_id: 0 },
    });
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalled());
  });

  it("clears cached data when the realtime client stops (logout or account switch)", async () => {
    const { client, queryClient } = setup();
    queryClient.setQueryData(dataKey("users"), [{ id: 1 }]);
    client.stop();
    expect(queryClient.getQueryData(dataKey("users"))).toBeUndefined();
  });
});
