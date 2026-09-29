/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CorpusLlmActivityInspector from "../../src/components/CorpusLlmActivityInspector.vue";
import { corpusBuildsApi } from "../../src/api/corpus/builds";
import { realtime } from "../../src/realtime";
import type { RealtimeEvent } from "../../src/realtime/protocol";

describe("Corpus LLM activity inspector", () => {
  let handler: ((event: RealtimeEvent) => void) | undefined;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-29T02:00:00Z"));
    setActivePinia(createPinia());
    handler = undefined;
    vi.spyOn(realtime, "subscribe").mockImplementation((_topic, callback) => {
      handler = callback;
      return () => undefined;
    });
    vi.spyOn(corpusBuildsApi, "llmTrace").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(corpusBuildsApi, "llmLiveOutput").mockResolvedValue({ items: [], total: 0 });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("coalesces websocket progress into bounded, non-overlapping live-output reads", async () => {
    const wrapper = mount(CorpusLlmActivityInspector, { props: { buildId: "b1" } });
    const details = wrapper.get("details");
    (details.element as HTMLDetailsElement).open = true;
    await details.trigger("toggle");
    await flushPromises();

    expect(corpusBuildsApi.llmLiveOutput).toHaveBeenCalledTimes(1);
    expect(handler).toBeTypeOf("function");

    for (let seq = 1; seq <= 6; seq += 1) {
      handler?.({
        type: "corpus.llm_progress",
        event_id: seq,
        resource_type: "corpus_build",
        resource_id: "b1",
        revision: seq,
        timestamp: "2026-09-29T02:00:00Z",
        payload: {
          generation: {
            call_id: "b1:1",
            seq,
            chars: seq * 10,
            gap: false,
            final: false,
          },
        },
      });
    }

    await vi.advanceTimersByTimeAsync(749);
    expect(corpusBuildsApi.llmLiveOutput).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    await flushPromises();
    expect(corpusBuildsApi.llmLiveOutput).toHaveBeenCalledTimes(2);

    // Another burst inside the interval still produces only one trailing snapshot.
    for (let seq = 7; seq <= 12; seq += 1) {
      handler?.({
        type: "corpus.llm_progress",
        event_id: seq,
        resource_type: "corpus_build",
        resource_id: "b1",
        revision: seq,
        timestamp: "2026-09-29T02:00:01Z",
        payload: {
          generation: {
            call_id: "b1:1",
            seq,
            chars: seq * 10,
            gap: false,
            final: false,
          },
        },
      });
    }
    await vi.advanceTimersByTimeAsync(750);
    await flushPromises();
    expect(corpusBuildsApi.llmLiveOutput).toHaveBeenCalledTimes(3);

    wrapper.unmount();
  });
});
