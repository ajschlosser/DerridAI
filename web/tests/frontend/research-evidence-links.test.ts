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
  it("keeps long answer evidence compact until the reader asks for the full passage", async () => {
    const longText = "A".repeat(1100);
    const wrapper = mount(ResearchEvidencePanel, {
      props: {
        resultEvidence: [
          {
            evidence_id: "E1",
            full_citation: "Derrida, Jacques. Test Work.",
            collection: "derrida_primary",
            record: { record_id: "rec-1", work: "Test Work", text: longText },
          },
        ],
      },
    });

    const passage = wrapper.get(".research-evidence-text");
    expect(passage.text().length).toBeLessThan(longText.length);
    const expand = wrapper.get('.research-evidence-passage button[aria-expanded="false"]');
    await expand.trigger("click");
    expect(wrapper.get(".research-evidence-text").text()).toBe(longText);
    const collapse = wrapper.get('.research-evidence-passage button[aria-expanded="true"]');
    expect(collapse.attributes("aria-expanded")).toBe("true");
  });

  it("keeps secondary source details collapsed by default", () => {
    const wrapper = mount(ResearchEvidencePanel, {
      props: {
        resultEvidence: [
          {
            evidence_id: "E1",
            full_citation: "Derrida, Jacques. Test Work.",
            collection: "derrida_primary",
            rerank_score: 0.91,
            record: { record_id: "rec-1", work: "Test Work", text: "Evidence text." },
          },
        ],
      },
    });

    const disclosures = wrapper.findAll(".research-evidence-disclosure");
    expect(disclosures).toHaveLength(1);
    expect(disclosures[0].attributes("open")).toBeUndefined();
    expect(disclosures[0].text()).toContain("Derrida, Jacques. Test Work.");
  });
});
