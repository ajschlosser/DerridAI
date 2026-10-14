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
import CorpusRecordSizingSettings from "./CorpusRecordSizingSettings.vue";
const meta = {
  title: "Corpus Builder/Settings/Record Sizing",
  component: CorpusRecordSizingSettings,
  args: {
    modelValue: {
      preferred_record_chars: 1750,
      record_length_tolerance: 200,
      long_record_chars: 3500,
      absolute_record_chars: 6000,
    },
  },
} satisfies Meta<typeof CorpusRecordSizingSettings>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
export const WiderResearchChunks: Story = {
  args: {
    modelValue: {
      preferred_record_chars: 2400,
      record_length_tolerance: 250,
      long_record_chars: 4200,
      absolute_record_chars: 7000,
    },
  },
};
export const SmallRecords: Story = {
  args: {
    modelValue: {
      preferred_record_chars: 100,
      record_length_tolerance: 10,
      long_record_chars: 200,
      absolute_record_chars: 350,
    },
  },
};
export const CustomButInvalid: Story = {
  args: {
    modelValue: {
      preferred_record_chars: 1750,
      record_length_tolerance: 200,
      long_record_chars: 1500,
      absolute_record_chars: 1200,
    },
  },
};
