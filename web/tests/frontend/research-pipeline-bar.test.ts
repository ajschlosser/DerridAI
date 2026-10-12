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

import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import ResearchPipelineBar from "../../src/components/research/ResearchPipelineBar.vue";
import type { ResearchJob } from "../../src/types/research";

const job = (id: string, thread_id?: string, status = "running") =>
  ({ id, status, prompt: `Question ${id}`, thread_id }) as unknown as ResearchJob;

describe("ResearchPipelineBar", () => {
  it("lists every active run outside a thread", () => {
    setActivePinia(createPinia());
    const wrapper = mount(ResearchPipelineBar, {
      props: { jobs: [job("a", "t1"), job("b"), job("c", undefined, "completed")] },
    });
    expect(wrapper.findAll(".research-pipeline-chip")).toHaveLength(2);
  });

  it("in a thread, counts only other active runs on one compact line", async () => {
    setActivePinia(createPinia());
    const wrapper = mount(ResearchPipelineBar, {
      props: { jobs: [job("a", "t1"), job("b", "t2")], threadId: "t1" },
    });
    expect(wrapper.classes()).toContain("compact");
    expect(wrapper.find(".research-pipeline-chip").exists()).toBe(false);
    expect(wrapper.get("#research-pipeline-bar-title").text()).toMatch(/^1\b/);
    await wrapper.get(".research-text-action").trigger("click");
    expect(wrapper.emitted("openRuns")).toHaveLength(1);
    // The open thread's own run is shown on its turn, so no bar remains.
    await wrapper.setProps({ jobs: [job("a", "t1")] });
    expect(wrapper.find(".research-pipeline-bar").exists()).toBe(false);
  });
});
