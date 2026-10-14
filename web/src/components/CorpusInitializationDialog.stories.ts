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
import type { CorpusBuild } from "../api/pdfCorpus";
import CorpusInitializationDialog from "./CorpusInitializationDialog.vue";

const build = {
  build_id: "build-demo",
  source_filename: "On Cosmopolitanism and Forgiveness.pdf",
  status: "running",
  stage: "segmenting",
  progress: 0.18,
  record_count: 0,
  accepted_count: 0,
} as CorpusBuild;
const meta: Meta<typeof CorpusInitializationDialog> = {
  title: "Corpus Builder/Build/Initialization Dialog",
  component: CorpusInitializationDialog,
  args: { build },
};
export default meta;
type Story = StoryObj<typeof CorpusInitializationDialog>;
export const Segmenting: Story = {};
export const Reconciling: Story = {
  args: { build: { ...build, stage: "reconciling", progress: 0.37 } as CorpusBuild },
};
