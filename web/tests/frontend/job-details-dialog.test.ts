// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import JobDetailsDialog from "../../src/components/JobDetailsDialog.vue";
import {
  closeJobDetailsDialog,
  openJobDetailsDialog,
  useJobDetailsDialog,
  type JobDetailsRequest,
} from "../../src/composables/jobDetailsDialog";

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
  closeJobDetailsDialog();
});

function open(over: Partial<JobDetailsRequest> = {}) {
  openJobDetailsDialog({
    title: "Job details",
    subtitle: "job-1",
    facts: [{ name: "Operation", value: "llm" }],
    fatalError: "",
    requestJson: "{}",
    events: [],
    resultJson: "{}",
    cancel: "none",
    onCancel: () => undefined,
    openResult: null,
    ...over,
  });
}

describe("JobDetailsDialog", () => {
  it("renders job text as text, never as markup", async () => {
    const wrapper = mount(JobDetailsDialog, { attachTo: document.body });
    open({
      fatalError: "<img src=x>",
      events: [{ when: "now", stage: "<b>s</b>", detail: "d", latest: true }],
    });
    await flushPromises();
    expect(wrapper.find(".info.error").text()).toBe("<img src=x>");
    expect(wrapper.find(".job-event b").text()).toBe("<b>s</b>");
    expect(wrapper.find(".job-event.latest").exists()).toBe(true);
    wrapper.unmount();
  });

  it("closes before cancelling, and disables the button once cancelling", async () => {
    const wrapper = mount(JobDetailsDialog, { attachTo: document.body });
    const onCancel = vi.fn(() => {
      expect(useJobDetailsDialog().current.value).toBeNull();
    });
    open({ cancel: "cancel", onCancel });
    await flushPromises();
    await wrapper.find(".btn.danger").trigger("click");
    await flushPromises();
    expect(onCancel).toHaveBeenCalledOnce();
    open({ cancel: "cancelling" });
    await flushPromises();
    expect(wrapper.find(".btn.danger").exists()).toBe(false);
    expect(wrapper.find(".da button[disabled]").exists()).toBe(true);
    wrapper.unmount();
  });

  it("closes before opening the result", async () => {
    const wrapper = mount(JobDetailsDialog, { attachTo: document.body });
    const run = vi.fn(() => {
      expect(useJobDetailsDialog().current.value).toBeNull();
    });
    open({ openResult: { label: "Open result", run } });
    await flushPromises();
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(run).toHaveBeenCalledOnce();
    wrapper.unmount();
  });
});
