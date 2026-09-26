/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
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
      workspaceMode: "record",
      hasSelectedRecord: true,
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
  });
}

describe("Corpus Builder review toolbar", () => {
  it("forwards queue and search models without owning review state", async () => {
    const wrapper = mountToolbar();

    await wrapper.get('[data-review-queue="ready"]').trigger("click");
    expect(wrapper.emitted("update:queue")?.at(-1)).toEqual(["ready"]);

    await wrapper.get("#pdf-corpus-record-search").setValue("Levinas");
    expect(wrapper.emitted("update:query")?.at(-1)).toEqual(["Levinas"]);
  });

  it("forwards workspace, clean-accept, bulk, and paging actions", async () => {
    const wrapper = mountToolbar();

    const workspaceButtons = wrapper.findAll(".workspace-switcher button");
    await workspaceButtons[1].trigger("click");
    expect(wrapper.emitted("workspace")?.at(-1)).toEqual(["metadata"]);

    await wrapper.get(".review-bulk .primary").trigger("click");
    expect(wrapper.emitted("acceptClean")).toHaveLength(1);

    wrapper.findComponent(CorpusActionMenu).vm.$emit("select", "reject-selected");
    expect(wrapper.emitted("bulkAction")?.at(-1)).toEqual(["reject-selected"]);

    const pagerButtons = wrapper.findAll(".pager button");
    await pagerButtons[1].trigger("click");
    expect(wrapper.emitted("nextPage")).toHaveLength(1);
  });

  it("keeps detail workspaces unavailable until a record is selected", () => {
    const wrapper = mountToolbar({ hasSelectedRecord: false });
    const workspaceButtons = wrapper.findAll(".workspace-switcher button");

    expect(workspaceButtons[0].attributes("disabled")).toBeUndefined();
    expect(workspaceButtons[1].attributes("disabled")).toBeDefined();
    expect(workspaceButtons[2].attributes("disabled")).toBeDefined();
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
    expect(wrapper.get(".review-bulk .primary").attributes("disabled")).toBeDefined();
    expect(wrapper.get("#pdf-corpus-record-search").attributes("disabled")).toBeUndefined();
    expect(wrapper.findAll(".pager button")[1].attributes("disabled")).toBeUndefined();
  });
});
