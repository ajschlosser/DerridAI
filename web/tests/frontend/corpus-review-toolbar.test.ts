/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CorpusRecord } from "../../src/api/corpus";
import CorpusActionMenu from "../../src/components/CorpusActionMenu.vue";
import CorpusBulkMetadataEditor from "../../src/components/CorpusBulkMetadataEditor.vue";
import CorpusReviewToolbar from "../../src/components/corpus-builder/CorpusReviewToolbar.vue";

const records: CorpusRecord[] = [
  {
    record_id: "record-1",
    text: "Review me.",
    text_length: 10,
    source_block_ids: [],
    source_spans: [],
  },
];

function mountToolbar(overrides: Record<string, unknown> = {}) {
  return mount(CorpusReviewToolbar, {
    props: {
      queue: "all",
      query: "",
      total: 12,
      ready: 5,
      issues: 3,
      metadata: 2,
      topology: 1,
      sourceProblems: 0,
      accepted: 3,
      rejected: 1,
      bulkActionItems: [{ id: "reject-selected", label: "Reject selected" }],
      bulkActionFeedback: "",
      bulkMetadataOpen: false,
      schema: null,
      records,
      knownValues: {},
      regionTypes: [],
      discourseRoles: [],
      selectedCount: 1,
      bulkTotalCount: 12,
      bulkDisabled: false,
      pageNumber: 1,
      pageCount: 3,
      hasPreviousPage: false,
      hasNextPage: true,
      disabled: false,
      ...overrides,
    },
    global: { stubs: { Teleport: true } },
  });
}

describe("Corpus Builder review toolbar", () => {
  it("forwards queue and search models without owning review state", async () => {
    const wrapper = mountToolbar();

    await wrapper.get('[data-review-queue="ready"]').trigger("click");
    expect(wrapper.emitted("update:queue")?.at(-1)).toEqual(["ready"]);

    await wrapper.get("#pdf-corpus-record-search").setValue("Levinas");
    await wrapper.get("#pdf-corpus-record-search").trigger("keydown.enter");
    expect(wrapper.emitted("update:query")?.at(-1)).toEqual(["Levinas"]);
  });

  describe("search debounce", () => {
    afterEach(() => vi.useRealTimers());

    it("commits one query after typing pauses, not one per keystroke", async () => {
      vi.useFakeTimers();
      const wrapper = mountToolbar();
      const input = wrapper.get("#pdf-corpus-record-search");

      for (const text of ["L", "Le", "Lev", "Levi"]) {
        await input.setValue(text);
        vi.advanceTimersByTime(100);
      }
      expect(wrapper.emitted("update:query")).toBeUndefined();

      vi.advanceTimersByTime(300);
      expect(wrapper.emitted("update:query")).toEqual([["Levi"]]);
    });

    it("clears immediately and follows external query changes", async () => {
      vi.useFakeTimers();
      const wrapper = mountToolbar({ query: "abc" });
      const input = wrapper.get("#pdf-corpus-record-search");
      expect((input.element as HTMLInputElement).value).toBe("abc");

      await input.setValue("");
      expect(wrapper.emitted("update:query")?.at(-1)).toEqual([""]);

      await wrapper.setProps({ query: "record-9" });
      expect((input.element as HTMLInputElement).value).toBe("record-9");
      vi.advanceTimersByTime(1000);
      expect(wrapper.emitted("update:query")).toHaveLength(1);
    });
  });

  it("forwards clean-accept, bulk, and paging actions", async () => {
    const wrapper = mountToolbar();

    await wrapper.get(".review-bulk .variant-primary").trigger("click");
    expect(wrapper.emitted("acceptClean")).toBeUndefined();
    expect(wrapper.get(".accept-ready-dialog-copy").text()).toContain("review decision");
    await wrapper.get(".ui-dialog-footer .variant-primary").trigger("click");
    expect(wrapper.emitted("acceptClean")).toHaveLength(1);

    wrapper.findComponent(CorpusActionMenu).vm.$emit("select", "reject-selected");
    expect(wrapper.emitted("bulkAction")?.at(-1)).toEqual(["reject-selected"]);

    const pagerButtons = wrapper.findAll(".pager button");
    await pagerButtons[1].trigger("click");
    expect(wrapper.emitted("nextPage")).toHaveLength(1);
  });

  it("keeps bulk-editor mutation payloads owned by the parent", () => {
    const wrapper = mountToolbar({ bulkMetadataOpen: true });
    const editor = wrapper.findComponent(CorpusBulkMetadataEditor);

    editor.vm.$emit("apply", {
      changes: { speaker: "Derrida" },
      applyToAll: false,
    });
    expect(wrapper.emitted("bulkApply")?.at(-1)).toEqual([
      { changes: { speaker: "Derrida" }, applyToAll: false },
    ]);

    editor.vm.$emit("close");
    expect(wrapper.emitted("bulkClose")).toHaveLength(1);
  });

  it("disables queue/bulk actions while leaving search and paging behavior unchanged", () => {
    const wrapper = mountToolbar({ disabled: true });

    expect(wrapper.get('[data-review-queue="all"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get(".review-bulk .variant-primary").attributes("disabled")).toBeDefined();
    expect(wrapper.get("#pdf-corpus-record-search").attributes("disabled")).toBeUndefined();
    expect(wrapper.findAll(".pager button")[1].attributes("disabled")).toBeUndefined();
  });
});
