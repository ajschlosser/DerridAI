import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusEnrichmentChanges from "../../src/components/CorpusEnrichmentChanges.vue";

const record = (over: Record<string, unknown> = {}) => ({
  needs_review: true, speaker: "Jacques Derrida", stance: "critique", target: "hospitality",
  metadata_field_status: { speaker: { status: "llm_inferred" }, stance: { status: "llm_inferred" }, target: { status: "unresolved" } },
  metadata_enrichment_history: [{ run_id: "r1", model: "qwen3.5:4b", outcome: "enriched", added_fields: ["speaker"],
    replaced: [{ field: "stance", previous: "assertion", value: "critique" }],
    disputes: [{ field: "target", existing: "cities of refuge", proposed: "hospitality" }] }],
  ...over,
});
const mountWith = (r: Record<string, unknown>) => mount(CorpusEnrichmentChanges, { props: { record: r } });

describe("changes made by an enrichment pass", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("lists what was added, replaced and disputed", () => {
    const text = mountWith(record()).text();
    expect(text).toContain("Changed by the last enrichment pass");
    expect(text).toContain("qwen3.5:4b");
    expect(text).toMatch(/Added\s*speaker: Jacques Derrida/);
    expect(text).toContain("assertion");
    expect(text).toContain("kept “cities of refuge”; the pass proposed “hospitality”");
  });
  it("restores the previous value, or keeps or takes the proposal", async () => {
    const wrapper = mountWith(record());
    const button = (name: string) => wrapper.findAll("button").find(b => b.text() === name)!;
    await button("Restore previous").trigger("click");
    await button("Keep current").trigger("click");
    await button("Use proposed").trigger("click");
    expect(wrapper.emitted("resolve")).toEqual([["stance", "assertion"], ["target", "cities of refuge"], ["target", "hospitality"]]);
  });
  it("drops a change once a person has decided that field, and hides when nothing is left or the record is settled", () => {
    const decided = record({ metadata_field_status: { speaker: { status: "human_confirmed" }, stance: { status: "human_confirmed" }, target: { status: "human_confirmed" } } });
    expect(mountWith(decided).find("section").exists()).toBe(false);
    expect(mountWith(record({ needs_review: false })).find("section").exists()).toBe(false);
    expect(mountWith({ needs_review: true }).find("section").exists()).toBe(false);
  });
});
