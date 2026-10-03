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

import RecordFieldEditorDialog from "../../src/components/RecordFieldEditorDialog.vue";
import {
  closeRecordFieldEditorDialog,
  openRecordFieldEditorDialog,
} from "../../src/composables/recordFieldEditorDialog";
import { openMessageDialog } from "../../src/composables/messageDialog";
import {
  parseRecordEditorValue,
  recordEditorField,
  recordEditorKind,
} from "../../src/domain/recordEditorFields";

vi.mock("../../src/composables/messageDialog", () => ({ openMessageDialog: vi.fn() }));

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
  closeRecordFieldEditorDialog();
  vi.mocked(openMessageDialog).mockClear();
});

const label = (key: string) => key;

function open(save = vi.fn().mockResolvedValue(true)) {
  const record: Record<string, unknown> = {
    work: "Of Grammatology",
    year: 1967,
    flag: true,
    note: null,
    concepts: ["trace"],
    text: "There is nothing outside the text.",
  };
  openRecordFieldEditorDialog({
    title: "Edit record",
    subtitle: "rec-1",
    help: "",
    footerNote: "local",
    saveLabel: "Save changes",
    parseErrorTitle: "Could not save",
    sections: [
      {
        title: "All",
        fields: Object.keys(record).map((k) => recordEditorField(k, record[k], label)),
      },
    ],
    save,
  });
  return save;
}

describe("record editor fields", () => {
  it("chooses an editor by value type and parses it back", () => {
    expect(recordEditorKind("flag", false)).toBe("boolean");
    expect(recordEditorKind("text", "x")).toBe("text");
    expect(recordEditorKind("concepts", [])).toBe("json");
    expect(recordEditorKind("year", 1)).toBe("number");
    expect(recordEditorKind("note", null)).toBe("null");
    expect(recordEditorKind("work", "x")).toBe("string");
    expect(parseRecordEditorValue("number", "", false)).toBeNull();
    expect(parseRecordEditorValue("number", "1.5", false)).toBe(1.5);
    expect(parseRecordEditorValue("null", "", false)).toBeNull();
    expect(parseRecordEditorValue("null", "a", false)).toBe("a");
    expect(parseRecordEditorValue("json", '["a"]', false)).toEqual(["a"]);
    expect(() => parseRecordEditorValue("json", "[", false)).toThrow();
    expect(parseRecordEditorValue("boolean", "", true)).toBe(true);
  });
});

describe("RecordFieldEditorDialog", () => {
  it("saves every field with its original type", async () => {
    const wrapper = mount(RecordFieldEditorDialog, { attachTo: document.body });
    const save = open();
    await flushPromises();
    await wrapper.find("#recordField-work").setValue("De la grammatologie");
    await wrapper.find("#recordField-year").setValue("1967.5");
    await wrapper.find("input[type=checkbox]").setValue(false);
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(save).toHaveBeenCalledWith({
      work: "De la grammatologie",
      year: 1967.5,
      flag: false,
      note: null,
      concepts: ["trace"],
      text: "There is nothing outside the text.",
    });
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps the dialog open and names the problem when JSON does not parse", async () => {
    const wrapper = mount(RecordFieldEditorDialog, { attachTo: document.body });
    const save = open();
    await flushPromises();
    await wrapper.find("#recordField-concepts").setValue("[");
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(save).not.toHaveBeenCalled();
    expect(openMessageDialog).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Could not save", tone: "danger" }),
    );
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    wrapper.unmount();
  });

  it("stays open when the save reports failure", async () => {
    const wrapper = mount(RecordFieldEditorDialog, { attachTo: document.body });
    open(vi.fn().mockResolvedValue(false));
    await flushPromises();
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    wrapper.unmount();
  });
});
