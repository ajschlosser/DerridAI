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
import { beforeAll, describe, expect, it, vi } from "vitest";
import SeparateWorksDialog from "../../src/components/SeparateWorksDialog.vue";
import { useMessageDialog } from "../../src/composables/messageDialog";
import {
  closeSeparateWorksDialog,
  openSeparateWorksDialog,
} from "../../src/composables/separateWorksDialog";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

const sources = [
  {
    id: "a",
    name: "a.jsonl",
    recordCount: 3,
    groups: [
      { work: "One", count: 2, defaultChecked: true },
      { work: "Untitled", count: 1, defaultChecked: false },
    ],
  },
  {
    id: "b",
    name: "b.jsonl",
    recordCount: 2,
    groups: [{ work: "Two", count: 2, defaultChecked: true }],
  },
];

describe("SeparateWorksDialog", () => {
  it("leaves untitled groups unchecked and submits the chosen works for the chosen source", async () => {
    const confirm = vi.fn().mockResolvedValue(undefined);
    const wrapper = mount(SeparateWorksDialog, { attachTo: document.body });
    openSeparateWorksDialog({ sources, confirm });
    await flushPromises();
    let boxes = wrapper.findAll(".separate-work-row input");
    expect(boxes.map((box) => (box.element as HTMLInputElement).checked)).toEqual([true, false]);
    await wrapper.find("select").setValue("b");
    boxes = wrapper.findAll(".separate-work-row input");
    expect(boxes).toHaveLength(1);
    await wrapper.find(".check-item input").setValue(true);
    await wrapper.find("button.primary").trigger("click");
    await flushPromises();
    expect(confirm).toHaveBeenCalledWith({ fileId: "b", works: ["Two"], removeFromSource: true });
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("does nothing when no work is selected", async () => {
    const confirm = vi.fn();
    const wrapper = mount(SeparateWorksDialog, { attachTo: document.body });
    openSeparateWorksDialog({ sources, confirm });
    await flushPromises();
    await wrapper.find(".separate-work-row input").setValue(false);
    await wrapper.find("button.primary").trigger("click");
    expect(confirm).not.toHaveBeenCalled();
    closeSeparateWorksDialog();
    wrapper.unmount();
  });

  it("stays open and reports the error when the split fails", async () => {
    const confirm = vi.fn().mockRejectedValue(new Error("disk full"));
    const wrapper = mount(SeparateWorksDialog, { attachTo: document.body });
    openSeparateWorksDialog({ sources, confirm });
    await flushPromises();
    await wrapper.find("button.primary").trigger("click");
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    expect(useMessageDialog().queue.value[0]?.message).toBe("disk full");
    closeSeparateWorksDialog();
    wrapper.unmount();
  });
});
