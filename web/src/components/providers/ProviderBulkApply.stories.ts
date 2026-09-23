/* Copyright 2026 Aaron John Schlosser, PhD. */
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
