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
import TopbarChrome from "./TopbarChrome.vue";

const languages = [
  { code: "en-US", name: "English", flag: "🇺🇸" },
  { code: "fr-CA", name: "Français", flag: "🇨🇦" },
];

const meta = {
  title: "Shell/Topbar Chrome",
  component: TopbarChrome,
  render: (args) => ({
    components: { TopbarChrome },
    setup: () => ({ args }),
    template:
      '<div style="display:flex;justify-content:flex-end;padding:12px;background:var(--card)"><TopbarChrome v-bind="args" /></div>',
  }),
  args: {
    username: "aaron",
    role: "admin",
    roleName: "Administrator",
    isAdmin: true,
    canFaq: true,
    canSettings: true,
    languages,
    locale: "en-US",
  },
} satisfies Meta<typeof TopbarChrome>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Administrator: Story = {};
export const Researcher: Story = {
  args: { role: "researcher", roleName: "Researcher", isAdmin: false, canFaq: false },
};
export const French: Story = {
  parameters: { locale: "fr-CA" },
  args: { locale: "fr-CA" },
};
