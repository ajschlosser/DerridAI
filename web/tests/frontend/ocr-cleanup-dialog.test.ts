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

import OcrCleanupDialog from "../../src/components/OcrCleanupDialog.vue";
import {
  closeOcrCleanupDialog,
  openOcrCleanupDialog,
  useOcrCleanupDialog,
} from "../../src/composables/ocrCleanupDialog";

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
  closeOcrCleanupDialog();
});

function open(over: Record<string, unknown> = {}) {
  const choose = vi.fn().mockResolvedValue(undefined);
  openOcrCleanupDialog({
    active: { name: "a.jsonl", recordCount: 2 },
    selectedCount: 0,
    reviewCount: 1,
    allCount: 5,
    fileCount: 2,
    choose,
    ...over,
  });
  return choose;
}

describe("OcrCleanupDialog", () => {
  it("closes first, then reports the chosen scope", async () => {
    const wrapper = mount(OcrCleanupDialog, { attachTo: document.body });
    const choose = open();
    await flushPromises();
    await wrapper.findAll(".scope-card")[2].trigger("click");
    await flushPromises();
    expect(choose).toHaveBeenCalledWith("review");
    expect(useOcrCleanupDialog().current.value).toBeNull();
    wrapper.unmount();
  });

  it("disables the scopes that have nothing to clean", async () => {
    const wrapper = mount(OcrCleanupDialog, { attachTo: document.body });
    const choose = open({ active: null });
    await flushPromises();
    const cards = wrapper.findAll(".scope-card");
    expect(cards[0].attributes("disabled")).toBeDefined();
    expect(cards[1].attributes("disabled")).toBeDefined();
    expect(cards[3].attributes("disabled")).toBeUndefined();
    await cards[0].trigger("click");
    expect(choose).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
