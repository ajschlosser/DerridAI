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
import { beforeAll, describe, expect, it } from "vitest";
import MixedWorkValuesDialog from "../../src/components/MixedWorkValuesDialog.vue";
import {
  closeMixedWorkValuesDialog,
  openMixedWorkValuesDialog,
} from "../../src/composables/mixedWorkValuesDialog";
import { useI18nStore } from "../../src/stores/i18n";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

describe("MixedWorkValuesDialog", () => {
  it("lists each variant with counts, unset values and truncated files, then closes", async () => {
    useI18nStore().dictionary = { "ui.unset": "Non défini", "ui.done": "Terminé" };
    const wrapper = mount(MixedWorkValuesDialog, { attachTo: document.body });
    openMixedWorkValuesDialog({
      work: "W",
      fieldLabel: "Year",
      recordCount: 5,
      values: [
        { text: "1967", files: ["a", "b", "c", "d"], count: 4 },
        { text: null, files: ["e"], count: 1 },
      ],
    });
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    expect(wrapper.find("h2").text()).toBe("Year");
    const rows = wrapper.findAll(".mixed-value-row");
    expect(rows).toHaveLength(2);
    expect(rows[0].find(".mixed-value-copy small").text()).toBe("a · b · c · +1");
    expect(rows[1].find("b").text()).toBe("Non défini");
    await wrapper.find("button.primary").trigger("click");
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    closeMixedWorkValuesDialog();
    wrapper.unmount();
  });
});
