import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { ProviderProfile } from "../api/system";
import MetadataEnrichmentDialog from "./MetadataEnrichmentDialog.vue";
const profiles: ProviderProfile[] = [
  { id: "primary", name: "Gemma second reader", type: "ollama", model: "gemma-4-26B" },
];
const meta = {
  title: "Corpus Builder/Review/Metadata Enrichment Dialog",
  component: MetadataEnrichmentDialog,
  args: { open: true, profiles, providerProfileId: "primary", recordCount: 82, acceptedCount: 71 },
} satisfies Meta<typeof MetadataEnrichmentDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
