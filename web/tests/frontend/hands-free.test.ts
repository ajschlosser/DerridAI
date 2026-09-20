import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusHandsFreeSettings from "../../src/components/CorpusHandsFreeSettings.vue";
import CorpusHandsFreeReport from "../../src/components/CorpusHandsFreeReport.vue";

const policy = (over = {}) => ({ enabled: false, passes: 1, min_confidence: 0.8, unresolved: "best_guess" as const, accept_records: true, publish: false, ...over });

describe("hands-free settings", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("says plainly that no one reviews, and locks the rules until it is switched on", () => {
    const wrapper = mount(CorpusHandsFreeSettings, { props: { modelValue: policy() } });
    expect(wrapper.text()).toContain("No one reviews the records in this mode");
    expect(wrapper.get("fieldset").attributes("disabled")).toBeDefined();
    expect(mount(CorpusHandsFreeSettings, { props: { modelValue: policy({ enabled: true }) } }).get("fieldset").attributes("disabled")).toBeUndefined();
  });

  it("emits a changed copy of the policy and clamps the pass count", async () => {
    const wrapper = mount(CorpusHandsFreeSettings, { props: { modelValue: policy({ enabled: true }) } });
    await wrapper.get('input[type="number"]').setValue("9");
    await wrapper.get("select").setValue("leave");
    await wrapper.get('input[type="range"]').setValue("0.9");
    const emitted = wrapper.emitted("update:modelValue")!.map(e => e[0] as Record<string, unknown>);
    expect(emitted[0].passes).toBe(3);
    expect(emitted[1].unresolved).toBe("leave");
    expect(emitted[2].min_confidence).toBe(0.9);
  });

  it("publishing is off by default and needs its own switch", () => {
    const wrapper = mount(CorpusHandsFreeSettings, { props: { modelValue: policy({ enabled: true }) } });
    const publish = wrapper.findAll('input[type="checkbox"]').at(-1)!;
    expect((publish.element as HTMLInputElement).checked).toBe(false);
  });

  it("without the enable switch (running on an existing build) the rules are always live", () => {
    const wrapper = mount(CorpusHandsFreeSettings, { props: { modelValue: policy(), showEnable: false } });
    expect(wrapper.get("fieldset").attributes("disabled")).toBeUndefined();
    expect(wrapper.text()).not.toContain("Run hands-free after the build");
  });
});

describe("hands-free report", () => {
  beforeEach(() => setActivePinia(createPinia()));
  const report = { records: 60, accepted: 52, fields_filled: 130, left_for_review: 8, passes_run: 1, ran_at: "", policy: policy({ enabled: true }), notes: ["Not published: some records still need a person."],
    exceptions: [{ record_id: "rec-9", reasons: ["target is still unresolved"] }] };

  it("summarizes the run and lets a person open each exception", async () => {
    const wrapper = mount(CorpusHandsFreeReport, { props: { report } });
    expect(wrapper.text()).toContain("52 of 60 records accepted, 130 values taken from the model, 8 left for you.");
    expect(wrapper.text()).toContain("target is still unresolved");
    expect(wrapper.text()).toContain("and 7 more in the review queue");
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("open-record")).toEqual([["rec-9"]]);
  });
  it("shows nothing when there has been no run", () => {
    expect(mount(CorpusHandsFreeReport, { props: { report: null } }).find("section").exists()).toBe(false);
  });
});
