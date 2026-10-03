// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import LlmToolResultDialog from "../../src/components/LlmToolResultDialog.vue";
import {
  closeLlmToolResultDialog,
  openLlmToolResultDialog,
  useLlmToolResultDialog,
  type LlmToolResultRequest,
} from "../../src/composables/llmToolResultDialog";

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
  closeLlmToolResultDialog();
});

function open(over: Partial<LlmToolResultRequest> = {}) {
  openLlmToolResultDialog({
    title: "Clean page text",
    subtitle: "ollama · gemma",
    body: { kind: "clean_text", text: "<b>raw</b> text" },
    action: null,
    ...over,
  });
}

describe("LlmToolResultDialog", () => {
  it("renders result text as text, never as markup", async () => {
    const wrapper = mount(LlmToolResultDialog, { attachTo: document.body });
    open();
    await flushPromises();
    expect(wrapper.find(".llm-tool-text").text()).toBe("<b>raw</b> text");
    expect(wrapper.find(".llm-tool-text b").exists()).toBe(false);
    wrapper.unmount();
  });

  it("closes before running the follow-up action", async () => {
    const wrapper = mount(LlmToolResultDialog, { attachTo: document.body });
    const run = vi.fn(() => {
      expect(useLlmToolResultDialog().current.value).toBeNull();
    });
    open({ action: { label: "Use it", run } });
    await flushPromises();
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(run).toHaveBeenCalledOnce();
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("offers no follow-up action when the task has none", async () => {
    const wrapper = mount(LlmToolResultDialog, { attachTo: document.body });
    open({
      body: {
        kind: "rag_grade_batch",
        graded: 1,
        failed: 0,
        total: 1,
        errorsJson: "",
        errorCount: 0,
      },
    });
    await flushPromises();
    expect(wrapper.find(".btn.primary").exists()).toBe(false);
    expect(wrapper.find(".bulk-grade-result .info").exists()).toBe(true);
    wrapper.unmount();
  });
});
