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
import { describe, expect, it } from "vitest";
import ResearchAnswerContent from "../../src/components/research/ResearchAnswerContent.vue";
import type { ResearchResultEvidence } from "../../src/types/research";

function packet(id: string, citation: string): ResearchResultEvidence[] {
  return [{ evidence_id: id, inline_citation: citation }] as ResearchResultEvidence[];
}

describe("shared Research answer content", () => {
  it("renders structure and citations without requiring the thread audit to open", async () => {
    const wrapper = mount(ResearchAnswerContent, {
      props: {
        compact: true,
        answer:
          "### Attribution\n\nA **qualified** proposition [[E1]].\n\n1. First claim [E1]\n2. Second claim",
        evidence: packet("E1", "(Derrida 1997: 11)"),
      },
    });

    expect(wrapper.find("h4").text()).toBe("Attribution");
    expect(wrapper.find("strong").text()).toBe("qualified");
    expect(wrapper.findAll("ol li")).toHaveLength(2);
    expect(wrapper.findAll("button.thread-answer-citation")).toHaveLength(2);
    // Numbered markers; the run's citation stays in the accessible name.
    expect(wrapper.findAll("button.thread-answer-citation").map((b) => b.text())).toEqual([
      "1",
      "1",
    ]);
    expect(wrapper.find("button").attributes("aria-label")).toContain("(Derrida 1997: 11)");
    expect(wrapper.text()).not.toContain("[[E1]]");
    await wrapper.find("button.thread-answer-citation").trigger("click");
    expect(wrapper.emitted("evidence")?.[0]).toEqual([0]);
    wrapper.unmount();
  });

  it("rebinds a reused evidence marker when the selected turn changes", async () => {
    const wrapper = mount(ResearchAnswerContent, {
      props: {
        answer: "The source [[E1]].",
        evidence: packet("E1", "(Work A: 10)"),
      },
    });
    expect(wrapper.find("button").attributes("aria-label")).toContain("(Work A: 10)");
    await wrapper.setProps({ evidence: packet("E1", "(Work B: 40)") });
    expect(wrapper.find("button").attributes("aria-label")).toContain("(Work B: 40)");
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("evidence")?.[0]).toEqual([0]);
    wrapper.unmount();
  });

  it("opens each of several citations in one paragraph at its own evidence index", async () => {
    const wrapper = mount(ResearchAnswerContent, {
      props: {
        compact: true,
        answer: "First [[E0]], then [E1], and unresolved [[E7]], then [[E0]] again.",
        evidence: [
          { evidence_id: "E0", inline_citation: "(Work A: 1)" },
          { evidence_id: "E1", inline_citation: "(Work B: 2)" },
        ] as ResearchResultEvidence[],
      },
    });
    const buttons = wrapper.findAll("button.thread-answer-citation");
    // Numbered by first citation, so a repeated source keeps its number.
    expect(buttons.map((button) => button.text())).toEqual(["1", "2", "1"]);
    for (const button of buttons) await button.trigger("click");
    expect(wrapper.emitted("evidence")).toEqual([[0], [1], [0]]);
    expect(wrapper.text()).toContain("E7");
    wrapper.unmount();
  });

  it("replaces a parenthesis of bound citations with markers but keeps other parentheses", () => {
    const wrapper = mount(ResearchAnswerContent, {
      props: {
        answer:
          "Writing (Derrida 1965: 23-25; Derrida 1981: 95). Speech (see Derrida 1965: 23-25).",
        evidence: [
          { evidence_id: "E0", inline_citation: "Derrida 1965: 23-25" },
          { evidence_id: "E1", inline_citation: "Derrida 1981: 95" },
        ] as ResearchResultEvidence[],
      },
    });
    const text = wrapper.find("p").text().replace(/\s+/g, "");
    expect(text).toBe("Writing12.Speech(see1).");
    wrapper.unmount();
  });

  it("renders the Works Cited as an unnumbered MLA list with italic titles", () => {
    const wrapper = mount(ResearchAnswerContent, {
      props: {
        answer:
          "Presence [[E0]].\n\n**Works Cited**\n\nDerrida, Jacques. *De la grammatologie*. Éditions de Minuit, 1965.\n---. *Dissemination*. U of Chicago P, 1981.",
        evidence: [
          {
            evidence_id: "E0",
            inline_citation: "Derrida 1965: 23-25",
            mla_in_text: "(Derrida, *De la grammatologie* 23–25)",
          },
        ] as ResearchResultEvidence[],
      },
    });
    const entries = wrapper.findAll(".research-works-cited li");
    expect(entries.map((entry) => entry.text())).toEqual([
      "Derrida, Jacques. De la grammatologie. Éditions de Minuit, 1965.",
      "---. Dissemination. U of Chicago P, 1981.",
    ]);
    expect(entries[0].find("em").text()).toBe("De la grammatologie");
    expect(wrapper.find("ol").exists()).toBe(false);
    expect(wrapper.find("button").attributes("title")).toBe("(Derrida, De la grammatologie 23–25)");
    wrapper.unmount();
  });

  it("drops the numbers from a Works Cited saved before MLA", () => {
    const wrapper = mount(ResearchAnswerContent, {
      props: {
        answer:
          "Text.\n\n**Works Cited**\n\n1. Derrida, Jacques. Margins.\n2. Heidegger, Martin. Nietzsche.",
      },
    });
    expect(wrapper.findAll(".research-works-cited li").map((entry) => entry.text())).toEqual([
      "Derrida, Jacques. Margins.",
      "Heidegger, Martin. Nietzsche.",
    ]);
    wrapper.unmount();
  });

  it("does not convert unknown citations into links or interpret text as HTML", () => {
    const wrapper = mount(ResearchAnswerContent, {
      props: {
        answer: "Unknown [E9] and <script>not executable</script>.",
        evidence: packet("E1", "(Work A: 10)"),
      },
    });
    expect(wrapper.findAll("button")).toHaveLength(0);
    expect(wrapper.text()).toContain("<script>not executable</script>");
    expect(wrapper.find("script").exists()).toBe(false);
    wrapper.unmount();
  });
});
