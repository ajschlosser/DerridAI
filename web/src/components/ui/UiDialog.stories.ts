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
import UiDialog from "./UiDialog.vue";
import UiButton from "./UiButton.vue";
const meta = {
  title: "Foundations/Overlays/Dialog",
  component: UiDialog,
  args: {
    title: "Edit document metadata",
    description:
      "Document-level defaults are inherited by records unless a record has a human override.",
    open: true,
  },
  render: (args) => ({
    components: { UiDialog, UiButton },
    setup: () => ({ args }),
    template: `<UiDialog v-bind="args"><div style="display:grid;gap:12px"><label>Title <input class="control" value="On Cosmopolitanism and Forgiveness"></label><label>Author <input class="control" value="Jacques Derrida"></label></div><template #footer><span>2 unsaved changes</span><div style="display:flex;gap:8px"><UiButton label="Reset"/><UiButton variant="primary" label="Save changes"/></div></template></UiDialog>`,
  }),
} satisfies Meta<typeof UiDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    title: "Modifier les métadonnées du document",
    description:
      "Ces valeurs par défaut sont héritées par les notices, sauf lorsqu’une valeur a été remplacée explicitement par une personne.",
  },
};
