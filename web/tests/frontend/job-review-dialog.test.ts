// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import JobReviewDialog from "../../src/components/JobReviewDialog.vue";
import {
  closeJobReviewDialog,
  openJobReviewDialog,
  type JobReviewActions,
  type JobReviewRow,
  type JobReviewView,
} from "../../src/composables/jobReviewDialog";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

beforeEach(() => {
  setActivePinia(createPinia());
  closeJobReviewDialog();
});

const row = (over: Partial<JobReviewRow> = {}): JobReviewRow => ({
  recordId: "r-1",
  copyKey: "k1",
  stale: false,
  isText: false,
  field: "Work",
  currentHtml: "a",
  proposedHtml: "b",
  rationale: "",
  ...over,
});

const view = (over: Partial<JobReviewView> = {}): JobReviewView => ({
  title: "LLM review changes",
  subtitle: "2/4",
  active: false,
  completed: 2,
  remaining: 0,
  noChangeCount: 0,
  resolution: {
    acceptedResults: 0,
    acceptedFields: 0,
    rejectedResults: 0,
    rejectedFields: 0,
    state: "pending",
  },
  failures: [],
  rows: [row(), row({ recordId: "r-2", isText: true, field: "Text" })],
  unchanged: [],
  discard: "none",
  hasSuccessful: true,
  ...over,
});

const actions = (over: Partial<JobReviewActions> = {}): JobReviewActions => ({
  apply: vi.fn(async () => true),
  rejectSelected: vi.fn(async () => true),
  discard: vi.fn(),
  refresh: vi.fn(),
  previewRow: vi.fn(),
  previewUnchanged: vi.fn(),
  onClose: vi.fn(),
  ...over,
});

describe("JobReviewDialog", () => {
  it("selects every field except the record text by default", async () => {
    const wrapper = mount(JobReviewDialog, { attachTo: document.body });
    const a = actions();
    openJobReviewDialog(view(), a);
    await flushPromises();
    const boxes = wrapper.findAll<HTMLInputElement>("input[type=checkbox]");
    expect(boxes.map((box) => box.element.checked)).toEqual([true, false]);
    await wrapper.find(".btn.primary").trigger("click");
    expect(a.apply).toHaveBeenCalledWith("selected", [0]);
    wrapper.unmount();
  });

  it("keeps the selection across a republished view and drops indices that vanished", async () => {
    const wrapper = mount(JobReviewDialog, { attachTo: document.body });
    const handle = openJobReviewDialog(view(), actions());
    await flushPromises();
    await wrapper.findAll("input[type=checkbox]")[1].setValue(true);
    handle.update(view({ subtitle: "3/4" }));
    await flushPromises();
    expect(
      wrapper.findAll<HTMLInputElement>("input[type=checkbox]").map((b) => b.element.checked),
    ).toEqual([true, true]);
    handle.update(view({ rows: [row()] }));
    await flushPromises();
    expect(
      wrapper.findAll<HTMLInputElement>("input[type=checkbox]").map((b) => b.element.checked),
    ).toEqual([true]);
    wrapper.unmount();
  });

  it("disables apply with nothing selected and reports close exactly once", async () => {
    const wrapper = mount(JobReviewDialog, { attachTo: document.body });
    const a = actions();
    const handle = openJobReviewDialog(view(), a);
    await flushPromises();
    const none = wrapper.findAll(".job-change-toolbar .btn")[1];
    await none.trigger("click");
    expect(wrapper.find(".btn.primary").attributes("disabled")).toBeDefined();
    handle.close();
    handle.close();
    await flushPromises();
    expect(a.onClose).toHaveBeenCalledOnce();
    expect(handle.isOpen()).toBe(false);
    wrapper.unmount();
  });

  it("renders record ids and failures as text", async () => {
    const wrapper = mount(JobReviewDialog, { attachTo: document.body });
    openJobReviewDialog(
      view({ failures: ["<i>x</i>: failed"], rows: [row({ recordId: "<b>r</b>" })] }),
      actions(),
    );
    await flushPromises();
    expect(wrapper.find(".info.warn").text()).toBe("<i>x</i>: failed");
    expect(wrapper.find(".job-record-cell b").text()).toBe("<b>r</b>");
    wrapper.unmount();
  });
});
