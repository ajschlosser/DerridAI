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
import LanguageFlag from "./LanguageFlag.vue";
const meta = {
  title: "Internationalization/Visuals/Language Flag",
  component: LanguageFlag,
  args: { code: "en-US", symbol: "🇺🇸", label: "English" },
} satisfies Meta<typeof LanguageFlag>;
export default meta;
type Story = StoryObj<typeof meta>;
export const UnitedStates: Story = {};
export const French: Story = { args: { code: "fr-CA", symbol: "🇨🇦", label: "Français" } };
export const NoFlag: Story = { args: { code: "eo", symbol: "", label: "Esperanto" } };
