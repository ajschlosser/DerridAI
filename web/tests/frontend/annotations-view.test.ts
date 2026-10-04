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
import { afterEach, describe, expect, it, vi } from "vitest";
import AnnotationsView from "../../src/views/AnnotationsView.vue";
import { annotationsService } from "../../src/services/annotations";
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

vi.mock("../../src/domain/sharedRecordWorkspace", () => ({ sharedRecordWorkspace: {} }));
vi.mock("../../src/domain/appBootstrap", () => ({}));
vi.mock("../../src/domain/sharedAnnotations", () => ({
  annotationsWorkspace: {
    loadAnnotationsWorkspace: vi.fn(async () => snapshot),
    setAnnotationsWorkspaceQuery: vi.fn(),
    setAnnotationsWorkspaceView: vi.fn(),
    openAnnotationsWorkspaceRecord: vi.fn(),
    openAnnotationsWorkspaceWork: vi.fn(),
    removeAnnotationsWorkspaceItem: vi.fn(async () => snapshot),
  },
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

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function refresh(wrapper: ReturnType<typeof mount>) {
  return (
    wrapper.vm as unknown as { annotations: { load(force: boolean): Promise<void> } }
  ).annotations.load(true);
}
afterEach(() => vi.restoreAllMocks());
describe("Annotations progressive reads", () => {
  it("mounts filters before a delayed read without claiming an empty corpus", async () => {
    const pending = deferred<typeof snapshot>();
    vi.spyOn(annotationsService, "loadWorkspace").mockReturnValueOnce(pending.promise);
    const wrapper = mount(AnnotationsView);
    await flushPromises();
    expect(wrapper.find('input[type="search"]').exists()).toBe(true);
    expect(wrapper.find(".ui-loading-state.is-skeleton").exists()).toBe(true);
    expect(wrapper.find(".llm-empty").exists()).toBe(false);
    pending.resolve(snapshot);
    await flushPromises();
    wrapper.unmount();
  });
  it("retains feed DOM and filter controls through refresh failure and retry", async () => {
    const read = vi.spyOn(annotationsService, "loadWorkspace").mockResolvedValue(snapshot);
    const wrapper = mount(AnnotationsView);
    await flushPromises();
    const feed = wrapper.get(".annotation-work-group").element;
    const pending = deferred<typeof snapshot>();
    read.mockReturnValueOnce(pending.promise);
    const operation = refresh(wrapper);
    await flushPromises();
    expect(wrapper.get(".annotation-work-group").element).toBe(feed);
    expect(wrapper.find(".ui-loading-state.is-inline").exists()).toBe(true);
    pending.reject(new Error("Unavailable"));
    await operation;
    await flushPromises();
    expect(wrapper.get(".annotation-work-group").element).toBe(feed);
    expect(wrapper.get('[role="alert"]').text()).toContain("Unavailable");
    await wrapper.get('[role="alert"] button').trigger("click");
    await flushPromises();
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    wrapper.unmount();
  });
  it("clears retained annotations when access is denied", async () => {
    const read = vi.spyOn(annotationsService, "loadWorkspace").mockResolvedValue(snapshot);
    const wrapper = mount(AnnotationsView);
    await flushPromises();
    read.mockRejectedValueOnce(Object.assign(new Error("Forbidden"), { status: 403 }));
    await refresh(wrapper);
    await flushPromises();
    expect(wrapper.find(".annotation-work-group").exists()).toBe(false);
    wrapper.unmount();
  });
  it("discards a superseded response", async () => {
    const older = deferred<typeof snapshot>();
    const read = vi.spyOn(annotationsService, "loadWorkspace").mockReturnValueOnce(older.promise);
    const wrapper = mount(AnnotationsView);
    read.mockResolvedValueOnce({ ...snapshot, groups: [] });
    await refresh(wrapper);
    older.resolve(snapshot);
    await flushPromises();
    expect(wrapper.find(".annotation-work-group").exists()).toBe(false);
    wrapper.unmount();
  });
  it("cancels a queued search on unmount", async () => {
    vi.useFakeTimers();
    const read = vi.spyOn(annotationsService, "loadWorkspace").mockResolvedValue(snapshot);
    const wrapper = mount(AnnotationsView);
    await flushPromises();
    await wrapper.get('input[type="search"]').setValue("trace");
    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(200);
    expect(read).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
