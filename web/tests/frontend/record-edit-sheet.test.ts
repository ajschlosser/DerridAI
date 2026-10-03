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
import { beforeEach, describe, expect, it } from "vitest";
import RecordEditSheet from "../../src/components/record/RecordEditSheet.vue";

function fieldLabel(wrapper: ReturnType<typeof mount>, text: string) {
  return wrapper.findAll("label").find((label) => label.find("span").text().trim() === text)!;
}

describe("RecordEditSheet metadata cardinality", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("keeps the closed editor unhydrated until it is opened", async () => {
    const wrapper = mount(RecordEditSheet, {
      attachTo: document.body,
      props: {
        open: false,
        record: { record_id: "r1", work: "First work" },
      },
    });
    await flushPromises();
    expect(wrapper.find(".record-edit-body input").exists()).toBe(false);

    await wrapper.setProps({ record: { record_id: "r2", work: "Second work" } });
    await flushPromises();
    expect(wrapper.find(".record-edit-body input").exists()).toBe(false);

    await wrapper.setProps({ open: true });
    await flushPromises();
    expect((fieldLabel(wrapper, "Record ID").get("input").element as HTMLInputElement).value).toBe(
      "r2",
    );
    expect((fieldLabel(wrapper, "Work").get("input").element as HTMLInputElement).value).toBe(
      "Second work",
    );

    wrapper.unmount();
  });

  it("does not infer known scalar cardinality from a legacy array value", async () => {
    const wrapper = mount(RecordEditSheet, {
      attachTo: document.body,
      props: {
        open: true,
        record: {
          record_id: "r1",
          quoted_speaker: ["Levinas", "Heidegger"],
          topics: ["hospitality", "democracy"],
        },
      },
    });
    await flushPromises();

    const quotedSpeaker = fieldLabel(wrapper, "Quoted speaker");
    expect((quotedSpeaker.get("input").element as HTMLInputElement).value).toBe(
      "Levinas | Heidegger",
    );
    expect(quotedSpeaker.find("small").exists()).toBe(false);

    const topics = fieldLabel(wrapper, "Topics");
    expect((topics.get("input").element as HTMLInputElement).value).toBe("hospitality, democracy");
    expect(topics.get("small").text()).toContain("Separate multiple values");

    wrapper.unmount();
  });
});
