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
import { researchThreadMarkdown } from "../../src/domain/researchThreadExport";
import type { ResearchThreadExport } from "../../src/types/researchThreads";

const tf = (key: string, values?: Record<string, string | number>) =>
  values ? `${key}(${Object.values(values).join(",")})` : key;

const data: ResearchThreadExport = {
  format: "derridai-research-thread-export-v1",
  thread: {
    thread_id: "rt_1",
    title: "Différance",
    created_at: "",
    updated_at: "",
    archived_at: null,
  },
  turns: [
    {
      turn_id: "u1",
      ordinal: 1,
      attempt: 2,
      status: "completed",
      question: "What is différance?",
      instructions: null,
      research_run_id: "run-1",
      job_id: "job-1",
      answer: "It is not a word (Derrida, Margins 3).",
      answer_available: true,
      provider: "ollama",
      model: "qwen",
      references: [
        {
          evidence_id: "E1",
          collection: "c",
          record_id: "r1",
          record_revision: 2,
          inline_citation: "(Derrida, Margins 3)",
          full_citation: "Derrida, Jacques. Margins.",
          locator: {},
        },
      ],
    },
    {
      turn_id: "u2",
      ordinal: 2,
      attempt: 1,
      status: "failed",
      question: "Second?",
      instructions: null,
      research_run_id: null,
      job_id: null,
      answer: null,
      answer_available: false,
      provider: null,
      model: null,
      references: [],
    },
  ],
  works_cited: ["Derrida, Jacques. Margins."],
};

describe("researchThreadMarkdown", () => {
  it("keeps run, attempt and Record identity and the run's own citations verbatim", () => {
    const md = researchThreadMarkdown(data, tf);
    expect(md).toContain("`run-1`");
    expect(md).toContain("research.export_attempt: 2");
    expect(md).toContain("- E1: Derrida, Jacques. Margins. — `c/r1` r2");
    expect(md).toContain("It is not a word (Derrida, Margins 3).");
    expect(md).toContain("1. Derrida, Jacques. Margins.");
  });

  it("marks a turn without an answer instead of inventing one", () => {
    const md = researchThreadMarkdown(data, tf);
    expect(md).toContain("_research.export_no_answer(failed)_");
    expect(md.split("## 2. Second?")[1]).not.toContain("research.export_references");
  });
});
