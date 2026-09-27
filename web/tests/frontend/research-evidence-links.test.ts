import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchEvidencePanel from "../../src/components/research/ResearchEvidencePanel.vue";

const evidence = [
  { evidence_id: "E1", collection: "derrida_primary", record: { record_id: "rec-1", work: "W" } },
];

describe("ResearchEvidencePanel links", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("links answer evidence to Record View, the relationship map, and the cELF model", async () => {
    const wrapper = mount(ResearchEvidencePanel, { props: { resultEvidence: evidence } });
    const buttons = wrapper.findAll(".research-evidence-links button");
    expect(buttons).toHaveLength(3);
    await buttons[0].trigger("click");
    await buttons[1].trigger("click");
    await buttons[2].trigger("click");
    expect(wrapper.emitted("openRecord")).toEqual([[0]]);
    expect(wrapper.emitted("openRelationships")).toEqual([
      [0, "trace"],
      [0, "model"],
    ]);
  });

  it("offers no links when the evidence has no durable record ID", () => {
    const wrapper = mount(ResearchEvidencePanel, {
      props: { resultEvidence: [{ evidence_id: "E1", record: {} }] },
    });
    expect(wrapper.find(".research-evidence-links").exists()).toBe(false);
  });
});
