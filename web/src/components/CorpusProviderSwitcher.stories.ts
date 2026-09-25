import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusProviderSwitcher from "./CorpusProviderSwitcher.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const profiles: any[] = [
  {
    id: "gemma26",
    name: "Gemma 4 26B",
    type: "ollama",
    model: "hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS",
  },
  { id: "qwen27", name: "Qwen 27B", type: "ollama", model: "Qwen3.8-27B" },
];
const meta = {
  title: "Corpus Builder/Enrichment/Provider Switcher",
  component: CorpusProviderSwitcher,
  args: {
    profiles,
    activeProfileId: "gemma26",
    activeModel: profiles[0].model,
    history: [
      {
        at: "2026-09-18T12:00:00Z",
        provider_profile_id: "qwen27",
        model: "Qwen3.8-27B",
        metadata_completed: 0,
      },
      {
        at: "2026-09-18T12:20:00Z",
        provider_profile_id: "gemma26",
        model: profiles[0].model,
        metadata_completed: 12,
      },
    ],
  },
} satisfies Meta<typeof CorpusProviderSwitcher>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
