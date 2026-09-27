/* Copyright 2026 Aaron John Schlosser, PhD. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RealtimeClient } from "../../src/realtime/client";
import { followResource } from "../../src/realtime/follow";
import { MockSocket, jobEvent } from "./realtime-support";

function liveClient() {
  const client = new RealtimeClient({
    createSocket: (url) => new MockSocket(url),
    url: () => "ws://t",
    random: () => 1,
  });
  client.start();
  MockSocket.instances[MockSocket.instances.length - 1].ready();
  return client;
}

describe("followResource", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockSocket.instances = [];
  });
  afterEach(() => vi.useRealTimers());

  it("refreshes on the resource's events and does not poll while live", async () => {
    const client = liveClient();
    const refresh = vi.fn(async () => {});
    followResource({ client, topic: "job:a", refresh, fallbackMs: 1000, minIntervalMs: 500 });
    await vi.advanceTimersByTimeAsync(10_000);
    expect(refresh).not.toHaveBeenCalled();

    const socket = MockSocket.instances[0];
    socket.frame(jobEvent(1, 1, { id: "a" }));
    socket.frame(jobEvent(2, 2, { id: "a" }));
    socket.frame(jobEvent(3, 3, { id: "a" }));
    await vi.advanceTimersByTimeAsync(0);
    expect(refresh).toHaveBeenCalledTimes(1); // a burst collapses into one read
    socket.frame(jobEvent(4, 4, { id: "a" }));
    await vi.advanceTimersByTimeAsync(500);
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it("polls over REST while the socket is unavailable, then stops when done", async () => {
    const client = liveClient();
    let done = false;
    const refresh = vi.fn(async () => {});
    followResource({ client, topic: "job:a", refresh, fallbackMs: 1000, isDone: () => done });
    MockSocket.instances[0].serverClose(1006);
    for (let i = 0; i < 3; i += 1) {
      MockSocket.instances[MockSocket.instances.length - 1].serverClose(1006);
      await vi.advanceTimersByTimeAsync(0);
    }
    expect(client.live).toBe(false);
    await vi.advanceTimersByTimeAsync(1000);
    expect(refresh).toHaveBeenCalledTimes(1);
    done = true;
    await vi.advanceTimersByTimeAsync(5000);
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it("reads once immediately when asked, through the same serialized path", async () => {
    const client = liveClient();
    const refresh = vi.fn(async () => {});
    const stop = followResource({ client, topic: "job:a", refresh, immediate: true });
    await vi.advanceTimersByTimeAsync(0);
    expect(refresh).toHaveBeenCalledTimes(1);
    stop();
    MockSocket.instances[0].frame(jobEvent(1, 1, { id: "a" }));
    await vi.advanceTimersByTimeAsync(1000);
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});
