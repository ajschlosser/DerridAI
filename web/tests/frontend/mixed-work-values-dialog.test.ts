// Copyright 2026 Aaron John Schlosser, PhD.
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
