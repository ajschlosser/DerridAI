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
import LlmTaskLauncherDialog from "./LlmTaskLauncherDialog.vue";
import { openLlmTaskLauncherDialog } from "../composables/llmTaskLauncherDialog";

const profile = (id: string, label: string, type: string, model: string) => ({
  id,
  label,
  type,
  model,
  autoModel: false,
  maxConcurrentRequests: 2,
  numCtx: 16384,
  think: "false",
  numPredict: 4096,
  temperature: 0,
  topP: 1,
  seed: "",
  extraOptions: "{}",
  available: true,
  statusError: "",
});

const meta = {
  title: "Jobs/LLM Task Launcher Dialog",
  component: LlmTaskLauncherDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { LlmTaskLauncherDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><LlmTaskLauncherDialog /></div>`,
    methods: {
      open() {
        openLlmTaskLauncherDialog({
          title: "Grade this answer",
          description: "Grades the answer against its cited evidence.",
          contextText: "What does Derrida mean by différance?",
          generationProvider: "ollama",
          generationModel: "gemma",
          profiles: [
            profile("a", "Local gemma", "ollama", "gemma"),
            profile("b", "Hosted", "openai", "gpt"),
          ],
          profileId: "a",
          runMode: "background",
          runModes: ["background", "foreground"],
          canManageProviders: true,
          manageProviders: () => undefined,
          warm: async () => "Model warm.",
          run: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof LlmTaskLauncherDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SameModelWarning: Story = {};
