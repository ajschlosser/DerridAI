/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SettingsSection from "./SettingsSection.vue";
import UiButton from "../ui/UiButton.vue";

const meta = {
  title: "Settings/Section",
  component: SettingsSection,
  render: (args) => ({
    components: {SettingsSection, UiButton},
    setup: () => ({args}),
    template: `<SettingsSection v-bind="args"><p>Retrieval k, rerank top N, and evidence budgets stay together.</p><template #actions><UiButton variant="primary" label="Save RAG defaults" /></template></SettingsSection>`,
  }),
  args: {
    sectionId: "retrieval",
    title: "RAG pipeline defaults",
    description: "Retrieval, fusion, reranking, and evidence-budget defaults.",
    persistence: "Saved in this browser",
    status: "dirty",
    statusLabel: "Unsaved changes",
  },
} satisfies Meta<typeof SettingsSection>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Unsaved: Story = {};
export const ReadOnly: Story = {args: {status: "readonly", statusLabel: "Read-only", persistence: "Managed elsewhere"}};
export const French: Story = {
  parameters: {locale: "fr-CA"},
  args: {
    title: "Valeurs par défaut du pipeline RAG",
    description: "Repérage, fusion, reclassement et budget de preuves.",
    persistence: "Enregistré dans ce navigateur",
    statusLabel: "Modifications non enregistrées",
  },
};
