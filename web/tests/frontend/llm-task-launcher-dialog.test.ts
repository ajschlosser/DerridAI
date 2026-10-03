// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import LlmTaskLauncherDialog from "../../src/components/LlmTaskLauncherDialog.vue";
import {
  closeLlmTaskLauncherDialog,
  openLlmTaskLauncherDialog,
  type LlmLauncherProfile,
  type LlmTaskLauncherRequest,
} from "../../src/composables/llmTaskLauncherDialog";

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
  closeLlmTaskLauncherDialog();
});

const profile = (id: string, type: string, model: string, over = {}): LlmLauncherProfile => ({
  id,
  label: id,
  type,
  model,
  autoModel: false,
  maxConcurrentRequests: 1,
  numCtx: 8192,
  think: "false",
  numPredict: 4096,
  temperature: 0,
  topP: 1,
  seed: "",
  extraOptions: "{}",
  available: true,
  statusError: "",
  ...over,
});

function open(over: Partial<LlmTaskLauncherRequest> = {}) {
  const request: LlmTaskLauncherRequest = {
    title: "Task",
    description: "",
    contextText: "",
    generationProvider: null,
    generationModel: null,
    profiles: [profile("a", "ollama", "m-a"), profile("b", "openai", "m-b")],
    profileId: "a",
    runMode: "background",
    runModes: ["background", "foreground"],
    canManageProviders: true,
    manageProviders: vi.fn(),
    warm: vi.fn(async () => "warm"),
    run: vi.fn(async () => true),
    ...over,
  };
  openLlmTaskLauncherDialog(request);
  return request;
}

describe("LlmTaskLauncherDialog", () => {
  it("submits the raw form values and closes when the run succeeds", async () => {
    const wrapper = mount(LlmTaskLauncherDialog, { attachTo: document.body });
    const request = open();
    await flushPromises();
    await wrapper.find("#toolModel").setValue("custom");
    await wrapper.find("#toolRunMode").setValue("foreground");
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(request.run).toHaveBeenCalledWith(
      expect.objectContaining({
        profileId: "a",
        runMode: "foreground",
        model: "custom",
        numCtx: "8192",
        numPredict: "4096",
        extraOptions: "{}",
      }),
    );
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("stays open when the run is refused and reloads settings when the profile changes", async () => {
    const wrapper = mount(LlmTaskLauncherDialog, { attachTo: document.body });
    open({ run: vi.fn(async () => false) });
    await flushPromises();
    await wrapper.find("#toolProvider").setValue("b");
    expect((wrapper.find("#toolModel").element as HTMLInputElement).value).toBe("m-b");
    expect(wrapper.find("#toolCtx").exists()).toBe(false);
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    wrapper.unmount();
  });

  it("warns when the grader is the model that generated the answer", async () => {
    const wrapper = mount(LlmTaskLauncherDialog, { attachTo: document.body });
    open({ generationProvider: "ollama", generationModel: "m-a" });
    await flushPromises();
    expect(wrapper.find(".info.warn").exists()).toBe(true);
    await wrapper.find("#toolProvider").setValue("b");
    expect(wrapper.find(".info.warn").exists()).toBe(false);
    wrapper.unmount();
  });

  it("locks the run mode to a single offered mode and hides provider management for researchers", async () => {
    const wrapper = mount(LlmTaskLauncherDialog, { attachTo: document.body });
    open({ runModes: ["foreground"], runMode: "foreground", canManageProviders: false });
    await flushPromises();
    const select = wrapper.find("#toolRunMode");
    expect(select.attributes("disabled")).toBeDefined();
    expect(select.findAll("option")).toHaveLength(1);
    expect(wrapper.findAll(".llm-tool-profile-actions button")).toHaveLength(1);
    wrapper.unmount();
  });

  it("shows the warm-up message from the caller", async () => {
    const wrapper = mount(LlmTaskLauncherDialog, { attachTo: document.body });
    open();
    await flushPromises();
    await wrapper.find(".llm-tool-profile-actions .btn").trigger("click");
    await flushPromises();
    expect(wrapper.find(".llm-tool-profile-actions [role=status]").text()).toBe("warm");
    wrapper.unmount();
  });
});
