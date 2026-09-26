/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { CorpusRecord } from "../../src/api/corpus";
import CorpusReviewRecordQueue from "../../src/components/corpus-builder/CorpusReviewRecordQueue.vue";

function record(overrides: Partial<CorpusRecord> = {}): CorpusRecord {
  return {
    record_id: "record-1",
    text: "A record under review.",
    text_length: 22,
    inline_citation: "Derrida, p. 12",
    source_block_ids: ["block-1"],
    source_spans: [],
    review_state: "ready",
    ...overrides,
  };
}

function mountQueue(overrides: Record<string, unknown> = {}) {
  return mount(CorpusReviewRecordQueue, {
    props: {
      records: [record()],
      recordTotal: 1,
      selectedRecordId: "record-1",
      selectedReviewIds: new Set<string>(),
      allVisibleSelected: false,
      loading: false,
      hydrated: true,
      disabled: false,
      ...overrides,
    },
  });
}

describe("Corpus Builder review record queue", () => {
  it("exposes the queue root used by focus and viewport restoration", () => {
    const wrapper = mountQueue();

    expect(wrapper.emitted("rootChange")?.[0]?.[0]).toBe(wrapper.get("nav").element);

    wrapper.unmount();
    expect(wrapper.emitted("rootChange")?.at(-1)).toEqual([null]);
  });

  it("preserves active-row and queue-selection semantics", async () => {
    const wrapper = mountQueue();

    expect(wrapper.get(".record-row").attributes("aria-current")).toBe("true");

    await wrapper.get(".record-select input").setValue(true);
    expect(wrapper.emitted("toggleRecord")?.at(-1)).toEqual(["record-1", true]);

    await wrapper.get(".select-visible input").setValue(true);
    expect(wrapper.emitted("toggleVisible")?.at(-1)).toEqual([true]);

    await wrapper.get(".record-row").trigger("click");
    expect(wrapper.emitted("selectRecord")?.at(-1)?.[0]).toMatchObject({
      record_id: "record-1",
    });
  });

  it("renders non-colour state cues and the LLM-processed marker", () => {
    const wrapper = mountQueue({
      records: [
        record({
          review_state: "ready",
          metadata_enrichment_finished: true,
        }),
      ],
    });

    expect(wrapper.get(".record-state-icon").attributes("data-state")).toBe("ready");
    expect(wrapper.find(".record-llm-processed").exists()).toBe(true);
  });

  it("surfaces source warnings as a dedicated action", async () => {
    const warned = record({
      source_quality_issues: [{ code: "ocr_noise", severity: "warning" }],
    });
    const wrapper = mountQueue({ records: [warned] });

    await wrapper.get(".record-source-warn").trigger("click");

    expect(wrapper.emitted("sourceWarning")?.at(-1)?.[0]).toMatchObject({
      record_id: "record-1",
    });
  });

  it("shows loading and empty recovery states", async () => {
    const loading = mountQueue({ records: [], recordTotal: 0, loading: true, hydrated: false });
    expect(loading.text()).toContain("Loading");

    const empty = mountQueue({ records: [], recordTotal: 0, loading: false, hydrated: true });
    await empty.get(".rail-empty button").trigger("click");
    expect(empty.emitted("showAll")).toHaveLength(1);
  });
});
