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
import PipelineEditorVersionDetails from "./PipelineEditorVersionDetails.vue";
import type { PipelineDefinition } from "../../types/pipelines";

const draft: PipelineDefinition = {
  pipeline_id: "reviewer_evidence",
  version: 8,
  name: "Reviewer Evidence Recovery",
  purpose: "evidence_suggestion",
  status: "draft",
  entry_stage_ids: ["query"],
  stages: [],
  notes: null,
};

const meta = {
  title: "Pipelines/Editor Version Details",
  component: PipelineEditorVersionDetails,
  args: { modelValue: draft },
} satisfies Meta<typeof PipelineEditorVersionDetails>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Collapsed: Story = {};

export const OpenWhenIdentityIncomplete: Story = {
  args: { modelValue: { ...draft, name: "" } },
};
