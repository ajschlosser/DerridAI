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

import type { Meta, StoryObj } from "@storybook/vue3";
import CorpusReviewQueueContext from "./CorpusReviewQueueContext.vue";

const meta = {
  title: "Corpus/Review Queue Context",
  component: CorpusReviewQueueContext,
  args: {
    currentRecordId: "record-002",
    justProcessedRecordId: "record-001",
    nextRecordId: "record-003",
  },
  render: (args) => ({
    components: { CorpusReviewQueueContext },
    setup: () => ({ args }),
    template:
      '<CorpusReviewQueueContext v-bind="args" @navigate-record="(recordId) => window.alert(recordId)" />',
  }),
} satisfies Meta<typeof CorpusReviewQueueContext>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const AtQueueEnd: Story = {
  args: {
    currentRecordId: "record-002",
    justProcessedRecordId: "record-001",
    nextRecordId: undefined,
  },
};
