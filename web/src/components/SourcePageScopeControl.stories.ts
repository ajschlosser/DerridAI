/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026 Aaron John Schlosser, PhD
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SourcePageScopeControl from "./SourcePageScopeControl.vue";

const meta = {
  title: "Corpus Builder/Setup/Source Page Scope",
  component: SourcePageScopeControl,
  args: {
    modelValue: [],
    pageCount: 240,
    pageDetection: {
      status: "detected",
      pattern: "bare",
      confidence: 0.98,
      marker_count: 240,
      first: 1,
      last: 240,
    },
    disabled: false,
  },
} satisfies Meta<typeof SourcePageScopeControl>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllPages: Story = {};

export const SelectedPages: Story = {
  args: {
    modelValue: [1, 2, 3, 17, 21, 22, 23, 24, 25],
  },
};

export const EstimatedDocxPages: Story = {
  args: {
    pageCount: 18,
    pageDetection: {
      status: "estimated",
      pattern: "word_count",
      confidence: 0,
      marker_count: 18,
      words_per_page: 300,
      one_record_per_page: true,
      confirmed: true,
    },
  },
};
