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

// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, h, ref } from "vue";
import CorpusBuildDetailsPanel from "../../src/components/CorpusBuildDetailsPanel.vue";

function panel() {
  return mount(CorpusBuildDetailsPanel, {
    props: { buildId: "b1", sourceFilename: "Source.pdf", warningCount: 100 },
    slots: {
      activity: '<div class="activity">Activity contents</div>',
      issues: '<div class="issues">Original warning</div>',
      settings: defineComponent({
        setup() {
          const value = ref("model");
          return () =>
            h("input", {
              class: "settings",
              value: value.value,
              onInput: (event: Event) => {
                value.value = (event.target as HTMLInputElement).value;
              },
            });
        },
      }),
    },
    global: {
      stubs: {
        UiDialog: {
          template:
            '<div role="dialog"><button class="close" @click="$emit(\'close\')">Close</button><slot /></div>',
        },
      },
    },
  });
}
describe("Build details panel", () => {
  it("mounts only the open section and exposes the warning count separately", async () => {
    const wrapper = panel();
    expect(wrapper.find(".activity").exists()).toBe(false);
    expect(wrapper.get(".issues-trigger").text()).toContain("100");
    await wrapper.get(".issues-trigger").trigger("click");
    expect(wrapper.find(".issues").exists()).toBe(true);
    expect(wrapper.find(".activity").exists()).toBe(false);
    const tabs = wrapper.findAll('[role="tab"]');
    await tabs[2].trigger("click");
    expect(wrapper.get(".issues").element.closest("section")!.hasAttribute("hidden")).toBe(true);
    expect(wrapper.find(".settings").exists()).toBe(true);
    await wrapper.get(".settings").setValue("pending-model");
    await tabs[0].trigger("click");
    await tabs[2].trigger("click");
    expect(wrapper.get<HTMLInputElement>(".settings").element.value).toBe("pending-model");
    await wrapper.get(".close").trigger("click");
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.emitted("openChange")).toEqual([[true], [false]]);
    wrapper.unmount();
  });
  it("supports arrow, Home and End navigation with one tabbable tab", async () => {
    const wrapper = panel();
    await wrapper.get(".build-details-launchers button").trigger("click");
    await wrapper.get('[role="tablist"]').trigger("keydown", { key: "ArrowLeft" });
    expect(wrapper.findAll('[role="tab"]')[2].attributes("aria-selected")).toBe("true");
    await wrapper.get('[role="tablist"]').trigger("keydown", { key: "Home" });
    expect(wrapper.find(".activity").exists()).toBe(true);
    await wrapper.get('[role="tablist"]').trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.find(".issues").exists()).toBe(true);
    await wrapper.get('[role="tablist"]').trigger("keydown", { key: "End" });
    expect(wrapper.findAll('[role="tab"][tabindex="0"]')).toHaveLength(1);
    const tab = wrapper.get('[role="tab"][tabindex="0"]');
    expect(wrapper.get('[role="tabpanel"]:not([hidden])').attributes("aria-labelledby")).toBe(
      tab.attributes("id"),
    );
    wrapper.unmount();
  });
  it("retains the active section on refresh but closes on a different build", async () => {
    const wrapper = panel();
    await wrapper.get(".issues-trigger").trigger("click");
    await wrapper.setProps({ warningCount: 101 });
    expect(wrapper.find(".issues").exists()).toBe(true);
    await wrapper.setProps({ buildId: "b2", sourceFilename: "Other.pdf", warningCount: 0 });
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.find(".issues-trigger").exists()).toBe(false);
    await wrapper.get(".build-details-launchers button").trigger("click");
    expect(wrapper.find(".activity").exists()).toBe(true);
    wrapper.unmount();
  });
});
