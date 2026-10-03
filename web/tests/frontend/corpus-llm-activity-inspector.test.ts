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
