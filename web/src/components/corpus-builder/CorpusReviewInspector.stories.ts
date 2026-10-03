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
import CorpusReviewInspector from "./CorpusReviewInspector.vue";

const meta = {
  title: "Corpus Builder/Review/Inspector",
  component: CorpusReviewInspector,
  args: { mode: "record", hasRecord: true, blockerCount: 2, tab: "metadata" },
  render: (args) => ({
    components: { CorpusReviewInspector },
    setup: () => ({ args }),
    template: `<div style="height: 24rem; display: grid"><CorpusReviewInspector v-bind="args">
      <section v-for="id in ['metadata', 'evidence', 'source', 'semantic']" :id="'review-panel-' + id" :key="id" role="tabpanel" :aria-labelledby="'review-tab-' + id" :hidden="args.tab !== id" tabindex="0" style="padding: 1rem">Active panel: {{ id }}</section>
    </CorpusReviewInspector></div>`,
  }),
} satisfies Meta<typeof CorpusReviewInspector>;
export default meta;
type Story = StoryObj<typeof meta>;

export const SplitView: Story = {};
export const EvidenceTab: Story = { args: { tab: "evidence", blockerCount: 0 } };
export const MetadataWorkspace: Story = { args: { mode: "metadata" } };
export const SourceWorkspace: Story = { args: { mode: "source" } };
