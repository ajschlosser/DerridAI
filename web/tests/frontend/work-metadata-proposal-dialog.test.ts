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
import WorkMetadataProposalDialog from "../../src/components/WorkMetadataProposalDialog.vue";
import {
  closeWorkMetadataProposalDialog,
  openWorkMetadataProposalDialog,
  useWorkMetadataProposalDialog,
  type WorkMetadataProposalEntry,
} from "../../src/composables/workMetadataProposalDialog";

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
  closeWorkMetadataProposalDialog();
});

const entry = (field: string, proposed: string): WorkMetadataProposalEntry => ({
  work: "W",
  recordCount: 3,
  fieldLabel: field,
  current: "old",
  proposed,
  rationale: "",
  confidence: 0.5,
});

function open(apply = vi.fn().mockResolvedValue(true)) {
  openWorkMetadataProposalDialog({
    jobLabel: "job",
    entries: [entry("Publisher", "P"), entry("Year", "1976")],
    unmatched: [{ work: "X", message: "" }],
    apply,
  });
  return apply;
}

describe("WorkMetadataProposalDialog", () => {
  it("applies every proposal by default, with edited text, then closes", async () => {
    const wrapper = mount(WorkMetadataProposalDialog, { attachTo: document.body });
    const apply = open();
    await flushPromises();
    await wrapper.findAll("textarea")[1].setValue("1977");
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(apply).toHaveBeenCalledWith([
      { index: 0, value: "P" },
      { index: 1, value: "1977" },
    ]);
    expect(useWorkMetadataProposalDialog().current.value).toBeNull();
    wrapper.unmount();
  });

  it("sends only the ticked rows and does not apply when none are ticked", async () => {
    const wrapper = mount(WorkMetadataProposalDialog, { attachTo: document.body });
    const apply = open();
    await flushPromises();
    await wrapper.findAll("input[type=checkbox]")[0].setValue(false);
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(apply).toHaveBeenCalledWith([{ index: 1, value: "1976" }]);

    open(apply.mockClear());
    await flushPromises();
    const clear = wrapper.findAll(".work-proposal-toolbar button")[1];
    await clear.trigger("click");
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(apply).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("stays open when apply reports a validation problem", async () => {
    const wrapper = mount(WorkMetadataProposalDialog, { attachTo: document.body });
    open(vi.fn().mockResolvedValue(false));
    await flushPromises();
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(useWorkMetadataProposalDialog().current.value).not.toBeNull();
    expect(wrapper.find("button.btn.primary").attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });
});
