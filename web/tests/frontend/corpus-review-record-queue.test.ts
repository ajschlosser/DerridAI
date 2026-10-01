/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { CorpusRecord } from "../../src/api/corpus";
import { queueRowFromRecord } from "../../src/features/corpus-builder/domain/queueRows";
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

function row(overrides: Partial<CorpusRecord> = {}) {
  return queueRowFromRecord(record(overrides));
}

function mountQueue(overrides: Record<string, unknown> = {}) {
  return mount(CorpusReviewRecordQueue, {
    props: {
      rows: [row()],
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

  it("leads each row with the short sequence number but keeps the full ID for assistive technology", () => {
    const wrapper = mountQueue({
      rows: [row({ record_id: "derrida-jacques-on-cosmopolitanism-00012" })],
    });
    const head = wrapper.get(".record-row-head b");
    expect(head.get("[aria-hidden='true']").text()).toBe("#12");
    expect(head.get(".sr-only").text()).toBe("derrida-jacques-on-cosmopolitanism-00012");
    expect(head.attributes("title")).toBe("derrida-jacques-on-cosmopolitanism-00012");
  });

  it("pages the list from a footer that appears only when there is more than one page", async () => {
    const single = mountQueue({ pageNumber: 1, pageCount: 1 });
    expect(single.find(".pager").exists()).toBe(false);
    const wrapper = mountQueue({
      pageNumber: 2,
      pageCount: 3,
      hasPreviousPage: true,
      hasNextPage: true,
    });
    expect(wrapper.get(".pager").text()).toContain("2 / 3");
    const [previous, next] = wrapper.findAll(".pager button");
    await previous.trigger("click");
    await next.trigger("click");
    expect(wrapper.emitted("previousPage")).toHaveLength(1);
    expect(wrapper.emitted("nextPage")).toHaveLength(1);
  });

  it("shows an ID without a trailing sequence number unchanged", () => {
    const wrapper = mountQueue({ rows: [row({ record_id: "intro" })] });
    expect(wrapper.get(".record-row-head b [aria-hidden='true']").text()).toBe("intro");
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
      rows: [
        row({
          review_state: "ready",
          metadata_enrichment_finished: true,
        }),
      ],
    });

    expect(wrapper.get(".record-state-icon").attributes("data-state")).toBe("ready");
    expect(wrapper.find(".record-llm-processed").exists()).toBe(true);
  });

  it("surfaces source warnings as a dedicated action", async () => {
    const warned = row({
      source_quality_issues: [{ code: "ocr_noise", severity: "warning" }],
    });
    const wrapper = mountQueue({ rows: [warned] });

    await wrapper.get(".record-source-warn").trigger("click");

    expect(wrapper.emitted("sourceWarning")?.at(-1)?.[0]).toMatchObject({
      record_id: "record-1",
    });
  });

  it("shows loading and empty recovery states", async () => {
    const loading = mountQueue({ rows: [], recordTotal: 0, loading: true, hydrated: false });
    expect(loading.text()).toContain("Loading");

    const empty = mountQueue({ rows: [], recordTotal: 0, loading: false, hydrated: true });
    await empty.get(".rail-empty button").trigger("click");
    expect(empty.emitted("showAll")).toHaveLength(1);
  });
});
