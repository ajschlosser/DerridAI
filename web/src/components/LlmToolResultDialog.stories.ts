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
import LlmToolResultDialog from "./LlmToolResultDialog.vue";
import {
  openLlmToolResultDialog,
  type LlmToolResultRequest,
} from "../composables/llmToolResultDialog";

function story(request: LlmToolResultRequest) {
  return {
    render: () => ({
      components: { LlmToolResultDialog },
      template: `<div><button class="btn" type="button" @click="open">Open</button><LlmToolResultDialog /></div>`,
      methods: {
        open() {
          openLlmToolResultDialog(request);
        },
      },
    }),
  };
}

const meta = {
  title: "Jobs/LLM Tool Result Dialog",
  component: LlmToolResultDialog,
  parameters: { layout: "centered" },
} satisfies Meta<typeof LlmToolResultDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CleanedText: Story = story({
  title: "Clean page text",
  subtitle: "ollama · gemma",
  body: { kind: "clean_text", text: "There is nothing outside the text." },
  action: { label: "Use as current page text", run: () => undefined },
});

export const BatchGradeWithErrors: Story = story({
  title: "Grade responses",
  subtitle: "ollama · gemma",
  body: {
    kind: "rag_grade_batch",
    graded: 8,
    failed: 2,
    total: 10,
    errorsJson: '[{"response":"r-3","error":"timeout"}]',
    errorCount: 1,
  },
  action: null,
});
