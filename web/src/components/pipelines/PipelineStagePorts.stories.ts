/* Copyright 2026 Aaron John Schlosser, PhD. */
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
