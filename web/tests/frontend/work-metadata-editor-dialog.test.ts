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
import WorkMetadataEditorDialog from "../../src/components/WorkMetadataEditorDialog.vue";
import {
  closeWorkMetadataEditorDialog,
  openWorkMetadataEditorDialog,
  type WorkMetadataField,
} from "../../src/composables/workMetadataEditor";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

const fields: WorkMetadataField[] = [
  { field: "publisher", label: "Publisher", kind: "text", mixed: true, mixedCount: 2, initial: "" },
  { field: "year", label: "Year", kind: "number", mixed: false, mixedCount: 0, initial: "1967" },
  { field: "flag", label: "Flag", kind: "boolean", mixed: false, mixedCount: 0, initial: "true" },
];

function open(apply = vi.fn().mockResolvedValue(true), inspectMixed = vi.fn()) {
  openWorkMetadataEditorDialog({
    work: "W",
    recordCount: 4,
    fileCount: 2,
    fields,
    inspectMixed,
    apply,
  });
  return { apply, inspectMixed };
}

describe("WorkMetadataEditorDialog", () => {
  it("submits only the ticked fields with their edited raw values, then closes", async () => {
    const wrapper = mount(WorkMetadataEditorDialog, { attachTo: document.body });
    const { apply } = open();
    await flushPromises();
    const rows = wrapper.findAll(".work-meta-row");
    expect(rows).toHaveLength(3);
    await rows[1].find("input[type=number]").setValue("1976");
    await rows[1].find("input[type=checkbox]").setValue(true);
    await rows[2].find("input[type=checkbox]").setValue(true);
    await wrapper.find("button.primary").trigger("click");
    await flushPromises();
    expect(apply).toHaveBeenCalledWith({ values: { year: "1976", flag: "true" } });
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps the editor open when the caller declines, and does nothing with no field ticked", async () => {
    const wrapper = mount(WorkMetadataEditorDialog, { attachTo: document.body });
    const { apply } = open(vi.fn().mockResolvedValue(false));
    await flushPromises();
    await wrapper.find("button.primary").trigger("click");
    expect(apply).not.toHaveBeenCalled();
    await wrapper.find(".work-meta-row input[type=checkbox]").setValue(true);
    await wrapper.find("button.primary").trigger("click");
    await flushPromises();
    expect(apply).toHaveBeenCalledOnce();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    expect(wrapper.find("button.primary").attributes("disabled")).toBeUndefined();
    closeWorkMetadataEditorDialog();
    wrapper.unmount();
  });

  it("offers the mixed-values inspector only for fields whose records disagree", async () => {
    const wrapper = mount(WorkMetadataEditorDialog, { attachTo: document.body });
    const { inspectMixed } = open();
    await flushPromises();
    const buttons = wrapper.findAll(".mixed-value-inspect");
    expect(buttons).toHaveLength(1);
    await buttons[0].trigger("click");
    expect(inspectMixed).toHaveBeenCalledWith("publisher");
    closeWorkMetadataEditorDialog();
    wrapper.unmount();
  });
});
