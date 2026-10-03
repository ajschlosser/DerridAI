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
import UiLoadingState from "./UiLoadingState.vue";

const meta = {
  title: "UI/UiLoadingState",
  component: UiLoadingState,
  parameters: {
    layout: "centered",
  },
  args: {
    label: "Loading works",
    detail: "Checking the local corpus database.",
  },
} satisfies Meta<typeof UiLoadingState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Status: Story = {};

export const Skeleton: Story = {
  args: {
    label: "Loading 24 work cards",
    variant: "skeleton",
    skeletonCount: 4,
  },
};

export const Inline: Story = { args: { label: "Updating…", detail: "", variant: "inline" } };
export const InlineFrench: Story = {
  args: {
    label: "Mise à jour…",
    detail: "Le contenu reste disponible pendant la mise à jour.",
    variant: "inline",
  },
};
