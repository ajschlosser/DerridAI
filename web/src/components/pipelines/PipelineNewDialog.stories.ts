/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineNewDialog from "./PipelineNewDialog.vue";
import { contractPurposes, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const meta = {
  title: "Pipelines/New Pipeline Dialog",
  component: PipelineNewDialog,
  args: { purposes: contractPurposes, vocabulary: contractVocabulary },
} satisfies Meta<typeof PipelineNewDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Choosing: Story = {};

export const WorkflowChosen: Story = { args: { initial: "research" } };

export const Starting: Story = { args: { initial: "research", busy: true } };

export const FrenchLengthStress: Story = {
  args: { initial: "evidence_suggestion" },
  parameters: { locale: "fr-CA" },
};
