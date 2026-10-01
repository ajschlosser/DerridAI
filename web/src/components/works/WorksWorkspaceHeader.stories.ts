/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import WorksWorkspaceHeader from "./WorksWorkspaceHeader.vue";

const meta = {
  title: "Works/Workspace Header",
  component: WorksWorkspaceHeader,
  args: {
    mode: "admin",
    canManageCorpus: true,
    canPopulate: true,
    canCreateSite: true,
    corpusManageDeniedReason: "Your role cannot load corpus files.",
    populateDisabledReason: "Add a provider profile to populate metadata.",
    createSiteDisabledReason: "Load at least one work first.",
  },
} satisfies Meta<typeof WorksWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof WorksWorkspaceHeader>;
export const Admin: Story = {};
export const Researcher: Story = { args: { mode: "researcher" } };
export const ActionsUnavailable: Story = {
  args: { canManageCorpus: false, canPopulate: false, canCreateSite: false },
};
