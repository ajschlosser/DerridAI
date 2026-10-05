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
import ResearchThreadNavigation from "./ResearchThreadNavigation.vue";
import { OrderedTurns } from "./ResearchThreadNavigation.stories";
const meta = {
  title: "Research/Thread answers",
  component: ResearchThreadNavigation,
} satisfies Meta<typeof ResearchThreadNavigation>;
export default meta;
type Story = StoryObj<typeof meta>;
export const InlineAnswers: Story = {
  args: OrderedTurns.args,
  render: (args) => ({
    components: { ResearchThreadNavigation },
    setup: () => ({ args }),
    template: `<ResearchThreadNavigation v-bind="args"><template #answer="{ turn }"><p style="white-space: pre-wrap">An illustrative answer to {{ turn.user_question }}.
Each turn retains its own citations and audit link.</p></template></ResearchThreadNavigation>`,
  }),
};
