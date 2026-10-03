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
import CorpusBuildDiagnostics from "./CorpusBuildDiagnostics.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Storybook fixture supplies only the fields diagnostics read.
const build: any = {
  build_id: "build-42",
  source_sha256: "0123456789abcdef",
  status: "awaiting_review",
  stage: "review",
  progress: 1,
  metadata_schema_version: "1.4.0",
  segmentation_prompt_version: "derrida-scholarly-v12",
  build_events: [
    { at: "2026-09-25T18:01:00Z", stage: "preparing", status: "running", progress: 0 },
  ],
};

const meta = {
  title: "Corpus Builder/Build/Diagnostics",
  component: CorpusBuildDiagnostics,
  args: {
    build,
    modelLabel: "qwen3.5:4b",
    runGuidance: [
      {
        field: "discourse_role",
        label: "Discourse role",
        instructions: "Prefer the narrower role.",
        lookFor: ["objection"],
      },
    ],
  },
} satisfies Meta<typeof CorpusBuildDiagnostics>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Collapsed: Story = {};
