/* Copyright 2026 Aaron John Schlosser, PhD. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RealtimeClient } from "../../src/realtime/client";
import { MockSocket, jobEvent } from "./realtime-support";

function client(overrides: Record<string, unknown> = {}) {
  return new RealtimeClient({
    url: () => "ws://test/api/ws/events",
    createSocket: (url) => new MockSocket(url),
    random: () => 1,
    baseBackoffMs: 1000,
    maxBackoffMs: 8000,
    fallbackAfterFailures: 3,
    ...overrides,
  });
}
const latest = () => MockSocket.instances[MockSocket.instances.length - 1];

describe("realtime client", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockSocket.instances = [];
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("connects, becomes ready and subscribes registered topics", () => {
    const rt = client();
    rt.subscribe("jobs", () => {});
    rt.start();
    expect(rt.status).toBe("connecting");
    latest().ready();
    expect(rt.status).toBe("connected");
    expect(rt.live).toBe(true);
    expect(latest().sent).toEqual([{ type: "subscribe", topics: ["jobs"] }]);
    rt.subscribe("job:a", () => {});
    expect(latest().sent[1]).toEqual({ type: "subscribe", topics: ["job:a"] });
  });

  it("delivers events once, in revision order, to the matching topics", () => {
    const rt = client();
    const all = vi.fn();
    const one = vi.fn();
    rt.subscribe("jobs", all);
    rt.subscribe("job:a", one);
    rt.start();
    latest().ready();
    latest().frame(jobEvent(1, 1, { id: "a", status: "running" }));
    latest().frame(jobEvent(1, 1, { id: "a", status: "running" })); // duplicate
    latest().frame(jobEvent(3, 3, { id: "a", completed: 3 }));
    latest().frame(jobEvent(4, 2, { id: "a", completed: 2 })); // stale revision
    latest().frame(jobEvent(5, 1, { id: "b" }));
    expect(all.mock.calls.map(([event]) => event.event_id)).toEqual([1, 3, 5]);
    expect(one.mock.calls.map(([event]) => event.event_id)).toEqual([1, 3]);
  });

  it("reconnects with exponential backoff, resubscribes and resumes from the last event", () => {
    const rt = client();
    rt.subscribe("jobs", () => {});
    rt.start();
    latest().ready();
    latest().frame(jobEvent(7, 1, { id: "a" }));
    latest().serverClose(1006);
    expect(rt.status).toBe("reconnecting");
    expect(MockSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(999);
    expect(MockSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(MockSocket.instances).toHaveLength(2);
    latest().ready(7);
    expect(latest().sent).toEqual([{ type: "subscribe", topics: ["jobs"], last_event_id: 7 }]);

    latest().serverClose(1006);
    vi.advanceTimersByTime(2000); // second attempt waits longer
    expect(MockSocket.instances).toHaveLength(3);
  });

  it("caps and jitters the backoff delay", () => {
    const rt = client({ random: () => 0 });
    rt.start();
    for (let attempt = 0; attempt < 8; attempt += 1) {
      latest().serverClose(1006);
      vi.runOnlyPendingTimers();
    }
    const before = MockSocket.instances.length;
    latest().serverClose(1006);
    vi.advanceTimersByTime(3999);
    expect(MockSocket.instances).toHaveLength(before);
    vi.advanceTimersByTime(1); // 8000ms cap * 0.5 jitter floor
    expect(MockSocket.instances).toHaveLength(before + 1);
  });

  it("asks the page to resync when the server cannot replay, and after a server restart", () => {
    const rt = client();
    const resync = vi.fn();
    rt.onResync(resync);
    rt.subscribe("jobs", () => {});
    rt.start();
    latest().ready();
    expect(resync).toHaveBeenLastCalledWith("connected");
    latest().frame(jobEvent(9, 4, { id: "a" }));
    latest().frame({
      type: "connection.resync_required",
      payload: { reason: "backpressure", last_event_id: 12 },
    });
    expect(resync).toHaveBeenLastCalledWith("backpressure");
    // Revisions reset, so a fresh stream for the same resource is accepted again.
    const handler = vi.fn();
    rt.subscribe("job:a", handler);
    latest().frame(jobEvent(13, 1, { id: "a" }));
    expect(handler).toHaveBeenCalledTimes(1);

    latest().serverClose(1012);
    vi.runOnlyPendingTimers();
    latest().ready(2); // the new server process restarted its event counter
    expect(resync).toHaveBeenLastCalledWith("server_restarted");
  });

  it("falls back after repeated failures and resyncs once when the socket recovers", () => {
    const rt = client();
    const resync = vi.fn();
    const statuses: Array<[string, boolean]> = [];
    rt.onResync(resync);
    rt.onStatus((status, fallback) => statuses.push([status, fallback]));
    rt.start();
    for (let attempt = 0; attempt < 3; attempt += 1) {
      latest().serverClose(1006);
      vi.runOnlyPendingTimers();
    }
    expect(rt.fallbackActive).toBe(true);
    expect(statuses).toContainEqual(["offline", true]);
    latest().ready();
    expect(rt.fallbackActive).toBe(false);
    expect(rt.status).toBe("connected");
    expect(resync).toHaveBeenCalledTimes(1);
  });

  it("stops for good on 4401 and reports the expired session", () => {
    const onAuthExpired = vi.fn();
    const rt = client({ onAuthExpired });
    rt.start();
    latest().ready();
    latest().serverClose(4401, "session expired");
    expect(onAuthExpired).toHaveBeenCalledTimes(1);
    // Polling continues until the app confirms the session over REST.
    expect(rt.fallbackActive).toBe(true);
    vi.advanceTimersByTime(60_000);
    expect(MockSocket.instances).toHaveLength(1);
  });

  it("treats a refused socket (4403) as fallback without hammering the server", () => {
    const rt = client();
    rt.start();
    latest().serverClose(4403, "realtime disabled");
    expect(rt.fallbackActive).toBe(true);
    vi.advanceTimersByTime(3999);
    expect(MockSocket.instances).toHaveLength(1);
  });

  it("closes on logout and reconnects fresh after login", () => {
    const rt = client();
    rt.subscribe("jobs", () => {});
    rt.start();
    latest().ready();
    latest().frame(jobEvent(5, 1, { id: "a" }));
    const first = latest();
    rt.stop();
    expect(first.closedWith).toBe(1000);
    expect(rt.status).toBe("idle");
    vi.advanceTimersByTime(60_000);
    expect(MockSocket.instances).toHaveLength(1);
    rt.start();
    latest().ready(5);
    // A new session does not claim to resume the previous user's stream.
    expect(latest().sent).toEqual([{ type: "subscribe", topics: ["jobs"] }]);
  });

  it("reconnects a silent socket after missed heartbeats", () => {
    const rt = client();
    rt.start();
    latest().ready(0, 2);
    // Health checks run every 1.5 s: degraded after 1.5 missed heartbeats, closed after 2.5.
    vi.advanceTimersByTime(4600);
    expect(rt.status).toBe("degraded");
    vi.advanceTimersByTime(1500);
    expect(latest().closedWith).toBe(4000);
    expect(rt.status).toBe("reconnecting");
  });

  it("unsubscribes a topic when its last handler leaves", () => {
    const rt = client();
    rt.start();
    latest().ready();
    const off = rt.subscribe("job:x", () => {});
    off();
    expect(latest().sent).toEqual([
      { type: "subscribe", topics: ["job:x"] },
      { type: "unsubscribe", topics: ["job:x"] },
    ]);
  });
});
