import type { Meta, StoryObj } from "@storybook/vue3";
import ResearchWorkspaceHeader from "./ResearchWorkspaceHeader.vue";
const meta:Meta<typeof ResearchWorkspaceHeader>={title:"Research/Research Workspace Header",component:ResearchWorkspaceHeader,args:{title:"Evidence-grounded research workspace",description:"Build a question, choose retrieval and generation settings, pin evidence, then run the provenance-aware pipeline.",evidenceCount:4,databaseCount:2}};export default meta;type Story=StoryObj<typeof ResearchWorkspaceHeader>;export const Default:Story={};
