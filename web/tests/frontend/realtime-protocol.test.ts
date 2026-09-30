/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { topicsForEvent, type RealtimeEvent } from "../../src/realtime/protocol";

function event(overrides: Partial<RealtimeEvent> & Pick<RealtimeEvent, "type">): RealtimeEvent {
  return {
    event_id: 1,
    resource_type: "job",
    resource_id: "r1",
    revision: 1,
    timestamp: "2026-09-27T00:00:00Z",
    payload: {} as never,
    ...overrides,
  } as RealtimeEvent;
}

describe("topicsForEvent", () => {
  it("delivers a streamed Research token only on the owning job's topic", () => {
    const topics = topicsForEvent(
      event({
        type: "llm.token",
        resource_type: "job",
        resource_id: "job-1",
        payload: { generation: { seq: 1, delta: "hi", gap: false, final: false } },
      }),
    );
    expect(topics).toEqual(["job:job-1"]);
  });

  it("delivers per-record metadata progress only on the owning build's topic", () => {
    for (const type of [
      "corpus.record_started",
      "corpus.field_checked",
      "corpus.record_completed",
    ] as const) {
      const topics = topicsForEvent(
        event({
          type,
          resource_type: "corpus_build",
          resource_id: "build-1",
          payload: { metadata: { record_id: "r1" } },
        }),
      );
      expect(topics).toEqual(["corpus-build:build-1"]);
    }
  });

  it("delivers background activity only on its own activity topic", () => {
    const topics = topicsForEvent(
      event({
        type: "activity.changed",
        resource_type: "activity",
        resource_id: "gutenberg",
        payload: { activity: { ready: false } },
      }),
    );
    expect(topics).toEqual(["activity:gutenberg"]);
  });

  it("still delivers ordinary job and corpus-build snapshots on the global feed and the resource topic", () => {
    expect(
      topicsForEvent(event({ type: "job.progress", resource_type: "job", resource_id: "job-1" })),
    ).toEqual(["jobs", "job:job-1"]);
    expect(
      topicsForEvent(
        event({
          type: "corpus.build_changed",
          resource_type: "corpus_build",
          resource_id: "build-1",
        }),
      ),
    ).toEqual(["corpus-builds", "corpus-build:build-1"]);
  });
});
