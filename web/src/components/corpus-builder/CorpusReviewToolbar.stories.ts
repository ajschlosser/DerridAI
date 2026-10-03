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
import CorpusReviewToolbar from "./CorpusReviewToolbar.vue";

const meta = {
  title: "Corpus Builder/Review/Toolbar",
  component: CorpusReviewToolbar,
  args: {
    queue: "all",
    query: "",
    total: 48,
    ready: 17,
    issues: 9,
    metadata: 5,
    topology: 3,
    sourceProblems: 1,
    accepted: 19,
    rejected: 3,
    bulkActionItems: [
      { id: "bulk-edit", label: "Bulk edit metadata" },
      { id: "reject-selected", label: "Reject selected" },
    ],
    bulkActionFeedback: "",
    bulkMetadataOpen: false,
    schema: null,
    knownValues: {},
    regionTypes: ["argument", "quotation"],
    discourseRoles: ["claim", "attribution"],
    selectedCount: 2,
    bulkTotalCount: 48,
    bulkDisabled: false,
    disabled: false,
  },
} satisfies Meta<typeof CorpusReviewToolbar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const IssuesQueue: Story = {
  args: {
    queue: "metadata",
    query: "Levinas",
  },
};

export const BulkFeedback: Story = {
  args: {
    bulkActionFeedback: "Updated metadata on 2 selected records.",
  },
};

export const Busy: Story = {
  args: {
    disabled: true,
    bulkDisabled: true,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
