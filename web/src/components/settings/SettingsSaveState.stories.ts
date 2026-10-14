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
import SettingsSaveState from "./SettingsSaveState.vue";

const meta = {
  title: "Settings/Save State",
  component: SettingsSaveState,
  args: { status: "saved", label: "Saved" },
} satisfies Meta<typeof SettingsSaveState>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Saved: Story = {};
export const Unsaved: Story = { args: { status: "dirty", label: "Unsaved changes" } };
export const Saving: Story = { args: { status: "saving", label: "Saving" } };
export const Succeeded: Story = { args: { status: "success", label: "Save succeeded" } };
export const Failed: Story = { args: { status: "failed", label: "Save failed" } };
export const ReadOnly: Story = { args: { status: "readonly", label: "Read-only" } };
export const French: Story = {
  parameters: { locale: "fr-CA" },
  args: { status: "dirty", label: "Modifications non enregistrées" },
};
