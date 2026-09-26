/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ProviderTuningFields from "./ProviderTuningFields.vue";
import type { ProviderProfile } from "../../api/system";

const meta = {
  title: "Providers/Tuning fields",
  component: ProviderTuningFields,
  args: {
    profile: { id: "o1", name: "Local Ollama", type: "ollama" } as ProviderProfile,
    sharedLimit: 1,
    sharedEndpoint: false,
  },
} satisfies Meta<typeof ProviderTuningFields>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ollama: Story = {};
export const SharedEndpoint: Story = { args: { sharedEndpoint: true } };
export const OpenAiCompatible: Story = {
  args: { profile: { id: "p1", name: "FreeLLM", type: "openai" } as ProviderProfile },
};
