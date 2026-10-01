import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuilderWorkspaceHeader from "./CorpusBuilderWorkspaceHeader.vue";

const meta = {
  title: "Corpus Builder/Workflow/Workspace Header",
  component: CorpusBuilderWorkspaceHeader,
  args: {
    sourceFilename: "Of Grammatology.pdf",
    buildId: "build-42",
    status: { label: "Reviewing", detail: "", tone: "info" },
    recordCount: 84,
    acceptedCount: 31,
    workspace: "review",
    steps: [
      { id: "setup", available: true, state: "complete" },
      { id: "build", available: true, state: "complete" },
      { id: "review", available: true, state: "current" },
      { id: "publish", available: true, state: "available" },
    ],
  },
} satisfies Meta<typeof CorpusBuilderWorkspaceHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveBuild: Story = {};

export const EmptyWorkspace: Story = {
  args: {
    sourceFilename: "",
    buildId: "",
    status: null,
    recordCount: 0,
    acceptedCount: 0,
    workspace: "setup",
    steps: [
      { id: "setup", available: true, state: "current" },
      { id: "build", available: false, state: "unavailable" },
      { id: "review", available: false, state: "unavailable" },
      { id: "publish", available: false, state: "unavailable" },
    ],
  },
};

export const Published: Story = {
  args: {
    publicationId: "publication-2026-09-25-001",
    status: { label: "Published", detail: "", tone: "success" },
    recordCount: 84,
    acceptedCount: 84,
    workspace: "publish",
    steps: [
      { id: "setup", available: true, state: "complete" },
      { id: "build", available: true, state: "complete" },
      { id: "review", available: true, state: "complete" },
      { id: "publish", available: true, state: "current" },
    ],
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    sourceFilename:
      "Jane Author — Cosmopolites de tous les pays, encore un effort ! — édition critique.pdf",
    status: { label: "Prêt à publier", detail: "", tone: "success" },
  },
};
