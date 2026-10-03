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

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineBenchmarkCaseList from "./PipelineBenchmarkCaseList.vue";
import type { ResearchPipelineBenchmarkCase } from "../../types/pipelines";

const item = (id: string, version: number): ResearchPipelineBenchmarkCase => ({
  case_id: id,
  version,
  prompt: "What is the trace?",
  source_collection: "derrida_primary",
  corpus_snapshot: { fingerprint: "a".repeat(64), collections: [], limitations: [] },
  created_at: "2026-09-29T20:00:00Z",
});

const meta = {
  title: "Pipelines/Benchmark Case List",
  component: PipelineBenchmarkCaseList,
  args: {
    cases: [item("trace-definition-001", 3), item("evidence-recovery-002", 1)],
    selectedKey: "trace-definition-001@3",
  },
} satisfies Meta<typeof PipelineBenchmarkCaseList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = { args: { cases: [], selectedKey: "" } };
