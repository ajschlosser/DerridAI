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
import ProviderBulkApply from "./ProviderBulkApply.vue";
import type { ProviderProfile } from "../../api/system";

const meta = {
  title: "Providers/Bulk apply",
  component: ProviderBulkApply,
  args: {
    profiles: [
      { id: "o1", name: "Local Ollama", type: "ollama" },
      { id: "p1", name: "FreeLLM", type: "openai" },
    ] as ProviderProfile[],
  },
} satisfies Meta<typeof ProviderBulkApply>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
