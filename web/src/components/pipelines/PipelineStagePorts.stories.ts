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
import PipelineStagePorts from "./PipelineStagePorts.vue";
import { analysisFixture } from "./fixtures/pipelineAnalysisFixture";
import type { PipelineStage } from "../../types/pipelines";

const stage: PipelineStage = {
  id: "b",
  strategy: "validate.provenance",
  enabled: true,
  config: {},
  next: ["c"],
};
const wiring = analysisFixture().wiring.stages;

const meta = {
  title: "Pipelines/Stage Inputs and Outputs",
  component: PipelineStagePorts,
  args: { stage, wiring: wiring.b },
  decorators: [() => ({ template: '<div style="max-width: 380px"><story /></div>' })],
} satisfies Meta<typeof PipelineStagePorts>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Connected: Story = {};

export const RunInputSource: Story = { args: { stage: { ...stage, id: "a" }, wiring: wiring.a } };

export const NotConnected: Story = {
  args: {
    wiring: {
      ...wiring.c,
      inputs: [{ ...wiring.c.inputs[0], status: "unbound", sources: [] }],
    },
  },
};

export const WrongType: Story = {
  args: {
    wiring: {
      ...wiring.c,
      inputs: [
        {
          ...wiring.c.inputs[0],
          status: "mismatch",
          explicit: true,
          sources: [
            {
              kind: "run_input",
              stage: null,
              output: null,
              name: "query",
              data_type: "query",
              via: "explicit",
              explicit: true,
              producer_enabled: true,
            },
          ],
        },
      ],
    },
  },
};

export const Loading: Story = { args: { wiring: null, loading: true } };

export const Unavailable: Story = { args: { wiring: null, error: "The server is unreachable." } };

export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };

export const FixedValueOnTuningPort: Story = {
  args: {
    stage: { ...stage, id: "pick", strategy: "select.top_k" },
    wiring: {
      ...wiring.c,
      inputs: [
        {
          port: "limit",
          data_type: "number",
          required: false,
          multiple: false,
          accepts_constant: true,
          minimum: 1,
          maximum: 1000,
          explicit: true,
          status: "bound",
          options: [],
          sources: [
            {
              kind: "constant",
              value: 5,
              stage: null,
              output: null,
              name: null,
              data_type: "number",
              via: "constant",
              explicit: true,
              producer_enabled: true,
            },
          ],
        },
      ],
    },
  },
};
