import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusTextNoiseSettings from "./CorpusTextNoiseSettings.vue";

const meta = {
  title: "Corpus Builder/Setup/Text Noise Settings",
  component: CorpusTextNoiseSettings,
  args: { threshold: 45, llmAssist: false },
} satisfies Meta<typeof CorpusTextNoiseSettings>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Strict: Story = { args: { threshold: 15 } };
export const LlmAssist: Story = { args: { llmAssist: true } };
