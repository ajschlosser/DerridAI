import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuilderWorkspaceHeader from "./CorpusBuilderWorkspaceHeader.vue";

const meta = {
  title: "Corpus Builder/Workflow/Workspace Header",
  component: CorpusBuilderWorkspaceHeader,
  args: {
    sourceFilename: "Of Grammatology.pdf",
    buildId: "build-42",
    stage: "review",
    status: "awaiting_review",
    recordCount: 84,
    acceptedCount: 31,
  },
} satisfies Meta<typeof CorpusBuilderWorkspaceHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveBuild: Story = {};

export const EmptyWorkspace: Story = {
  args: {
    sourceFilename: "",
    buildId: "",
    stage: "",
    status: "",
    recordCount: 0,
    acceptedCount: 0,
  },
};

export const Published: Story = {
  args: {
    publicationId: "publication-2026-09-25-001",
    stage: "published",
    status: "published",
    recordCount: 84,
    acceptedCount: 84,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    sourceFilename:
      "Jacques Derrida — Cosmopolites de tous les pays, encore un effort ! — édition critique.pdf",
    stage: "awaiting_review",
    status: "awaiting_review",
  },
};
