/* Copyright 2026 Aaron John Schlosser, PhD. */
// Why: the streamed Research draft (docs/USER_GUIDE.md) is advisory only — it must stop
// appending on a sequence gap, never regress on out-of-order delivery, and never leak one
// job's tokens into another job's draft when the reviewer switches jobs mid-stream.
import { describe, expect, it, vi } from "vitest";
import { realtime } from "../../src/realtime";
import type { EventHandler } from "../../src/realtime/client";
import { useResearchDraft } from "../../src/features/research/useResearchDraft";

function generationEvent(
  jobId: string,
  generation: { seq: number; delta: string; gap?: boolean; final?: boolean },
) {
  return {
    type: "llm.token",
    event_id: generation.seq,
    resource_type: "job",
    resource_id: jobId,
    revision: generation.seq,
    timestamp: "2026-01-01T00:00:00Z",
    payload: { generation: { gap: false, final: false, ...generation } },
  } as const;
}

describe("useResearchDraft", () => {
  it("accumulates deltas in order under the followed job's own topic", () => {
    const handlers = new Map<string, EventHandler>();
    const unsubscribe = vi.fn();
    vi.spyOn(realtime, "subscribe").mockImplementation((topic, handler) => {
      handlers.set(topic, handler);
      return unsubscribe;
    });

    const { draft, follow } = useResearchDraft();
    follow("job-1");
    expect(realtime.subscribe).toHaveBeenCalledWith("job:job-1", expect.any(Function));
    expect(draft.value).toEqual({ jobId: "job-1", text: "", gap: false, final: false });

    handlers.get("job:job-1")!(generationEvent("job-1", { seq: 1, delta: "The trace " }));
    handlers.get("job:job-1")!(generationEvent("job-1", { seq: 2, delta: "is not a presence." }));
    expect(draft.value).toEqual({
      jobId: "job-1",
      text: "The trace is not a presence.",
      gap: false,
      final: false,
    });

    vi.restoreAllMocks();
  });

  it("ignores out-of-order or duplicate deliveries", () => {
    const handlers = new Map<string, EventHandler>();
    vi.spyOn(realtime, "subscribe").mockImplementation((topic, handler) => {
      handlers.set(topic, handler);
      return vi.fn();
    });

    const { draft, follow } = useResearchDraft();
    follow("job-1");
    const handler = handlers.get("job:job-1")!;
    handler(generationEvent("job-1", { seq: 2, delta: "second " }));
    handler(generationEvent("job-1", { seq: 1, delta: "first " })); // arrives late: dropped
    handler(generationEvent("job-1", { seq: 2, delta: "second again " })); // duplicate: dropped
    expect(draft.value?.text).toBe("second ");

    vi.restoreAllMocks();
  });

  it("stops appending after a gap and waits for the final REST answer", () => {
    const handlers = new Map<string, EventHandler>();
    vi.spyOn(realtime, "subscribe").mockImplementation((topic, handler) => {
      handlers.set(topic, handler);
      return vi.fn();
    });

    const { draft, follow } = useResearchDraft();
    follow("job-1");
    const handler = handlers.get("job:job-1")!;
    handler(generationEvent("job-1", { seq: 1, delta: "kept " }));
    handler(generationEvent("job-1", { seq: 2, delta: "", gap: true }));
    handler(generationEvent("job-1", { seq: 3, delta: "dropped after gap" }));
    expect(draft.value).toEqual({ jobId: "job-1", text: "kept ", gap: true, final: false });

    vi.restoreAllMocks();
  });

  it("unsubscribes from the previous job when following a new one", () => {
    const handlers = new Map<string, EventHandler>();
    const unsubscribeFirst = vi.fn();
    vi.spyOn(realtime, "subscribe").mockImplementation((topic, handler) => {
      handlers.set(topic, handler);
      return topic === "job:job-1" ? unsubscribeFirst : vi.fn();
    });

    const { draft, follow } = useResearchDraft();
    follow("job-1");
    follow("job-2");
    expect(unsubscribeFirst).toHaveBeenCalledOnce();
    expect(draft.value).toEqual({ jobId: "job-2", text: "", gap: false, final: false });

    // A stale event for the no-longer-followed job never reaches the new draft.
    handlers.get("job:job-1")!(generationEvent("job-1", { seq: 1, delta: "stale" }));
    expect(draft.value?.text).toBe("");

    vi.restoreAllMocks();
  });

  it("unsubscribes once the stream reports its final delta", () => {
    const handlers = new Map<string, EventHandler>();
    const unsubscribe = vi.fn();
    vi.spyOn(realtime, "subscribe").mockImplementation((topic, handler) => {
      handlers.set(topic, handler);
      return unsubscribe;
    });

    const { draft, follow } = useResearchDraft();
    follow("job-1");
    handlers.get("job:job-1")!(generationEvent("job-1", { seq: 1, delta: "done.", final: true }));
    expect(unsubscribe).toHaveBeenCalledOnce();
    // The final text stays visible until the caller explicitly clears it.
    expect(draft.value?.text).toBe("done.");

    vi.restoreAllMocks();
  });

  it("clear() drops the draft and stops the subscription", () => {
    const unsubscribe = vi.fn();
    vi.spyOn(realtime, "subscribe").mockReturnValue(unsubscribe);

    const { draft, follow, clear } = useResearchDraft();
    follow("job-1");
    clear();
    expect(unsubscribe).toHaveBeenCalledOnce();
    expect(draft.value).toBeNull();

    vi.restoreAllMocks();
  });
});
