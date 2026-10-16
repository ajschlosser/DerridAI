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
import ResearchTurnInspector from "../../src/components/research/ResearchTurnInspector.vue";
import type { ResearchResult } from "../../src/types/research";

const result = {
  answer: "The trace precedes presence [[E0]]. It is différance [[E0]].",
  evidence: [
    {
      evidence_id: "E0",
      inline_citation: "Derrida, Of Grammatology: 61",
      record: { work: "Of Grammatology", text: "The trace…" },
    },
    {
      evidence_id: "E1",
      inline_citation: "Derrida, Of Grammatology: 65",
      record: { work: "Of Grammatology", text: "The (pure) trace…" },
    },
  ],
} as ResearchResult;

function badge(activeEvidenceIndex: number) {
  return mount(ResearchTurnInspector, {
    props: { result, activeEvidenceIndex, instanceId: "turn-1" },
  }).find(".research-evidence-cited");
}

describe("ResearchTurnInspector", () => {
  beforeEach(() => setActivePinia(createPinia()));

  // Regression: the inspector did not pass the answer to the evidence panel,
  // so every item in a thread turn was labelled "Retrieved, not cited".
  it("counts citations of the turn's own answer for each evidence item", () => {
    expect(badge(0).classes()).not.toContain("uncited");
    expect(badge(0).text()).toMatch(/2/);
    expect(badge(1).classes()).toContain("uncited");
  });
});
