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

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusUnreviewedPublishDialog from "../../src/components/CorpusUnreviewedPublishDialog.vue";

describe("CorpusUnreviewedPublishDialog", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("shows review scope and emits an explicit publication decision", async () => {
    const wrapper = mount(CorpusUnreviewedPublishDialog, {
      props: { open: true, pendingRecords: 7, unresolvedFields: 12 },
      global: {
        stubs: {
          Teleport: true,
          UiDialog: {
            props: ["open", "title", "description"],
            template:
              '<section v-if="open" role="dialog"><h2>{{ title }}</h2><p>{{ description }}</p><slot/><slot name="footer"/></section>',
          },
          UiButton: {
            props: ["label", "disabled"],
            emits: ["click"],
            template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>',
          },
          AppIcon: true,
        },
      },
    });

    expect(wrapper.text()).toContain("7");
    expect(wrapper.text()).toContain("12");
    expect(wrapper.text()).toContain("cELF Core and Publication conformance");

    const publish = wrapper
      .findAll("button")
      .find((button) => button.text() === "Publish suggestions as-is");
    expect(publish).toBeTruthy();
    await publish!.trigger("click");
    expect(wrapper.emitted("confirm")).toHaveLength(1);
  });

  it("does not turn the primary action into a destructive control", () => {
    const wrapper = mount(CorpusUnreviewedPublishDialog, {
      props: { open: true },
      global: {
        stubs: {
          UiDialog: { template: '<div><slot/><slot name="footer"/></div>' },
          UiButton: {
            props: ["label", "variant"],
            template: '<button :data-variant="variant">{{ label }}</button>',
          },
          AppIcon: true,
        },
      },
    });

    expect(wrapper.find('button[data-variant="primary"]').text()).toBe("Publish suggestions as-is");
    expect(wrapper.find('button[data-variant="danger"]').exists()).toBe(false);
  });
});
