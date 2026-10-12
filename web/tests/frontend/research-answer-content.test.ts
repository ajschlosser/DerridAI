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
    expect(wrapper.text()).toContain("(Derrida 1997: 11)");
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
    expect(wrapper.find("button").text()).toBe("(Work A: 10)");
    await wrapper.setProps({ evidence: packet("E1", "(Work B: 40)") });
    expect(wrapper.find("button").text()).toBe("(Work B: 40)");
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("evidence")?.[0]).toEqual([0]);
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
