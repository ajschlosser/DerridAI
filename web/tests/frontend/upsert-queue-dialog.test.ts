// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import UpsertQueueDialog from "../../src/components/UpsertQueueDialog.vue";
import {
  closeUpsertQueueDialog,
  openUpsertQueueDialog,
  type UpsertQueueItem,
} from "../../src/composables/upsertQueueDialog";

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
  closeUpsertQueueDialog();
});

const item = (key: string): UpsertQueueItem => ({
  key,
  recordId: `rec-${key}`,
  source: "Work · file.jsonl",
  status: { kind: "changed", label: "Changed" },
  changes: [{ field: "speaker", source: "manual", when: "", oldValue: "a", newValue: "b" }],
});

function open() {
  let items = [item("a"), item("b"), item("c")];
  const request = {
    store: "derrida",
    items: () => items,
    remove: vi.fn((key: string) => (items = items.filter((i) => i.key !== key))),
    sync: vi.fn().mockResolvedValue(undefined),
  };
  openUpsertQueueDialog(request);
  return request;
}

describe("UpsertQueueDialog", () => {
  it("syncs only the checked records, and drops a removed one from the list", async () => {
    const wrapper = mount(UpsertQueueDialog, { attachTo: document.body });
    const request = open();
    await flushPromises();
    expect(wrapper.findAll(".upsert-queue-card")).toHaveLength(3);
    await wrapper.findAll("input[type=checkbox]")[1].setValue(false);
    await wrapper.find(".btn.danger").trigger("click");
    expect(request.remove).toHaveBeenCalledWith("a");
    expect(wrapper.findAll(".upsert-queue-card")).toHaveLength(2);
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(request.sync).toHaveBeenCalledWith(["c"]);
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("does not sync when nothing is checked", async () => {
    const wrapper = mount(UpsertQueueDialog, { attachTo: document.body });
    const request = open();
    await flushPromises();
    await wrapper.findAll(".queue-bulk-actions .btn")[1].trigger("click");
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(request.sync).not.toHaveBeenCalled();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    wrapper.unmount();
  });

  it("reveals a record's changes on request", async () => {
    const wrapper = mount(UpsertQueueDialog, { attachTo: document.body });
    open();
    await flushPromises();
    const toggle = wrapper.find(".tools .btn");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    await toggle.trigger("click");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    wrapper.unmount();
  });
});
