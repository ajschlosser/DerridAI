/* Copyright 2026 Aaron John Schlosser, PhD. */
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
      {code: "en-US", name: "English", flag: ""},
      {code: "fr-CA", name: "Français", flag: ""},
    ] as never;
  });

  it("selects and closes files without treating close as select", async () => {
    const wrapper = mount(RecordsFileRail, {props: {files, canManage: true}});
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
    const wrapper = mount(RecordsFileRail, {props: {files, canManage: false}});
    expect(wrapper.find(".records-file-actions").exists()).toBe(false);
    expect(wrapper.find(".records-file-close").exists()).toBe(false);
    wrapper.unmount();
  });

  it("keeps merge disabled until two files are loaded", () => {
    const wrapper = mount(RecordsFileRail, {props: {files: [files[0]], canManage: true}});
    const merge = wrapper.findAll("button").find((button) => button.text().includes("Merge files"));
    expect(merge?.attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });
});
