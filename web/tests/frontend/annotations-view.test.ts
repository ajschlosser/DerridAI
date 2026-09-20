// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import AnnotationsView from "../../src/views/AnnotationsView.vue";
import AnnotationFeedItem from "../../src/components/annotations/AnnotationFeedItem.vue";

const snapshot = {
  query: "",
  view: "works" as const,
  total: 1,
  annotations: [],
  groups: [
    {
      work: "Writing and Difference",
      records: 1,
      annotations: [
        {
          id: "a1",
          record_id: "record-1",
          work: "Writing and Difference",
          field: "text",
          quote: "A trace is not a presence.",
          note: "Review this passage.",
          tags: ["trace"],
          author: "researcher",
          source: "corpus.jsonl",
          created_at: "2026-09-14T20:30:00Z",
          server: false,
          removable: true,
          local_file_id: "file-1",
          local_index: 0,
          local_annotation_index: 0,
          shared_annotation_id: null,
        },
      ],
    },
  ],
};

vi.mock("../../src/runtime/runtime.js", () => ({
  loadAnnotationsWorkspace: vi.fn(async () => snapshot),
  setAnnotationsWorkspaceQuery: vi.fn(),
  setAnnotationsWorkspaceView: vi.fn(),
  openAnnotationsWorkspaceRecord: vi.fn(),
  openAnnotationsWorkspaceWork: vi.fn(),
  removeAnnotationsWorkspaceItem: vi.fn(async () => snapshot),
  notifyToast: vi.fn(),
}));

describe("AnnotationsView", () => {
  it("renders grouped annotations and supports switching to recent", async () => {
    const wrapper = mount(AnnotationsView);
    await flushPromises();
    expect(wrapper.text()).toContain("Writing and Difference");
    expect(wrapper.text()).toContain("A trace is not a presence.");

    await wrapper.get(".view-tab:nth-child(2)").trigger("click");
    expect(wrapper.text()).toContain("Recent annotations");
  });
});

describe("AnnotationFeedItem", () => {
  it("emits open and remove actions", async () => {
    const annotation = snapshot.groups[0].annotations[0];
    const wrapper = mount(AnnotationFeedItem, { props: { annotation } });
    await wrapper.get(".annotation-open-record").trigger("click");
    await wrapper.get(".btn.danger").trigger("click");
    expect(wrapper.emitted("open")).toHaveLength(1);
    expect(wrapper.emitted("remove")).toHaveLength(1);
  });
});
