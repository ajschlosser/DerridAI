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
