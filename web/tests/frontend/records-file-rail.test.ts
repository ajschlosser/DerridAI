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
import RecordsFileRail from "../../src/components/records/RecordsFileRail.vue";
import { useI18nStore } from "../../src/stores/i18n";
import type { RecordsFileTab } from "../../src/domain/recordsFiles";

const files: RecordsFileTab[] = [
  {
    id: "f1",
    name: "glas.jsonl",
    count: 12,
    dirty: 0,
    active: true,
    origin: "imported",
    origin_detail: "",
  },
  {
    id: "f2",
    name: "glas-subset.jsonl",
    count: 4,
    dirty: 2,
    active: false,
    origin: "subset",
    origin_detail: "glas.jsonl",
  },
];

describe("RecordsFileRail", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().languages = [
      { code: "en-US", name: "English", flag: "" },
      { code: "fr-CA", name: "Français", flag: "" },
    ] as never;
  });

  it("selects and closes files without treating close as select", async () => {
    const wrapper = mount(RecordsFileRail, { props: { files, canManage: true } });
    expect(wrapper.text()).toContain("Local JSONL");
    expect(wrapper.text()).toContain("Imported");
    expect(wrapper.text()).toContain("Subset · glas.jsonl");
    expect(wrapper.text()).toContain("Edited since load");
    await wrapper.get('[aria-current="true"]').trigger("click");
    expect(wrapper.emitted("select")).toEqual([["f1"]]);
    await wrapper.get('button[aria-label="Close glas-subset.jsonl"]').trigger("click");
    expect(wrapper.emitted("close")).toEqual([["f2"]]);
    expect(wrapper.emitted("select")).toEqual([["f1"]]);
    wrapper.unmount();
  });

  it("hides file actions when the workspace cannot be managed", () => {
    const wrapper = mount(RecordsFileRail, { props: { files, canManage: false } });
    expect(wrapper.find(".records-file-actions").exists()).toBe(false);
    expect(wrapper.find(".records-file-close").exists()).toBe(false);
    wrapper.unmount();
  });

  it("keeps merge disabled until two files are loaded", () => {
    const wrapper = mount(RecordsFileRail, { props: { files: [files[0]], canManage: true } });
    const merge = wrapper.findAll("button").find((button) => button.text().includes("Merge files"));
    expect(merge?.attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });
});
