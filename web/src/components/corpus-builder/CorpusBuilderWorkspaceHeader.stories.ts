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
import CorpusBuilderWorkspaceHeader from "./CorpusBuilderWorkspaceHeader.vue";

const meta = {
  title: "Corpus Builder/Workflow/Workspace Header",
  component: CorpusBuilderWorkspaceHeader,
  args: {
    sourceFilename: "Of Grammatology.pdf",
    buildId: "build-42",
    status: { label: "Reviewing", detail: "", tone: "info" },
    recordCount: 84,
    acceptedCount: 31,
    workspace: "review",
    steps: [
      { id: "setup", available: true, state: "complete" },
      { id: "build", available: true, state: "complete" },
      { id: "review", available: true, state: "current" },
      { id: "publish", available: true, state: "available" },
    ],
  },
} satisfies Meta<typeof CorpusBuilderWorkspaceHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveBuild: Story = {};

export const EmptyWorkspace: Story = {
  args: {
    sourceFilename: "",
    buildId: "",
    status: null,
    recordCount: 0,
    acceptedCount: 0,
    workspace: "setup",
    steps: [
      { id: "setup", available: true, state: "current" },
      { id: "build", available: false, state: "unavailable" },
      { id: "review", available: false, state: "unavailable" },
      { id: "publish", available: false, state: "unavailable" },
    ],
  },
};

export const Published: Story = {
  args: {
    publicationId: "publication-2026-09-25-001",
    status: { label: "Published", detail: "", tone: "success" },
    recordCount: 84,
    acceptedCount: 84,
    workspace: "publish",
    steps: [
      { id: "setup", available: true, state: "complete" },
      { id: "build", available: true, state: "complete" },
      { id: "review", available: true, state: "complete" },
      { id: "publish", available: true, state: "current" },
    ],
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    sourceFilename:
      "Jacques Derrida — Cosmopolites de tous les pays, encore un effort ! — édition critique.pdf",
    status: { label: "Prêt à publier", detail: "", tone: "success" },
  },
};
