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
import CorpusReviewAdvancedMetadata from "./CorpusReviewAdvancedMetadata.vue";

const meta = {
  title: "Corpus Builder/Review/Advanced Metadata",
  component: CorpusReviewAdvancedMetadata,
  args: {
    busy: false,
    hasManifest: true,
    profiles: [],
    providerId: "",
    modelOverride: "",
    familyOptions: [
      { key: "discourse", label: "Discourse" },
      { key: "quotation", label: "Quotation" },
    ],
    draft: '{\n  "region_type": "argument"\n}',
    family: "all",
  },
  render: (args) => ({
    components: { CorpusReviewAdvancedMetadata },
    setup: () => ({ args }),
    template: `<div style="max-width: 32rem"><CorpusReviewAdvancedMetadata v-bind="args" open /></div>`,
  }),
} satisfies Meta<typeof CorpusReviewAdvancedMetadata>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Busy: Story = { args: { busy: true } };
