/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchEvidencePanel from "../../src/components/research/ResearchEvidencePanel.vue";

const evidence = [
  {
    evidence_id: "E1",
    inline_citation: "(OG 12)",
    full_citation: "Derrida, Of Grammatology, 12.",
    collection: "derrida",
    rerank_score: 0.9123,
    record: {
      work: "Of Grammatology",
      page_start: 12,
      text: "The passage itself.",
      speaker: "Derrida",
      position_holder: "Rousseau",
    },
  },
  {
    evidence_id: "E2",
    inline_citation: "(SP 4)",
    record: { work: "Speech and Phenomena", text: "Other." },
  },
];

function panel(activeIndex = 0) {
  return mount(ResearchEvidencePanel, {
    props: { resultEvidence: evidence as never, activeIndex, answer: "A (OG 12). B (OG 12)." },
  });
}

describe("ResearchEvidencePanel", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("shows the passage before attribution and keeps speaker and position holder apart", () => {
    const html = panel().find(".research-evidence-inspector").html();
    expect(html.indexOf("The passage itself.")).toBeLessThan(html.indexOf("Rousseau"));
    expect(html.indexOf("Derrida, Of Grammatology")).toBeLessThan(
      html.indexOf("research-relation-grid"),
    );
    const dds = panel()
      .findAll(".research-relation-grid dd")
      .map((dd) => dd.text());
    expect(dds).toEqual(["Derrida", "Rousseau"]);
  });

  it("counts how often the answer cites the active item", () => {
    expect(panel(0).find(".research-evidence-cited").text()).toContain("2");
    expect(panel(1).find(".research-evidence-cited").classes()).toContain("uncited");
  });

  it("puts retrieval diagnostics in a closed disclosure", () => {
    const details = panel().find("details.research-evidence-metadata");
    expect(details.exists()).toBe(true);
    expect(details.attributes("open")).toBeUndefined();
    expect(details.text()).toContain("0.912");
    expect(panel(1).find("details.research-evidence-metadata").exists()).toBe(false);
  });
});
