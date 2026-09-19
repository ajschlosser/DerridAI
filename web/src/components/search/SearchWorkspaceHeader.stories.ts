import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SearchWorkspaceHeader from "./SearchWorkspaceHeader.vue";

const meta:Meta<typeof SearchWorkspaceHeader>={
  title:"Search/Workspace Header",
  component:SearchWorkspaceHeader,
  args:{scope:"loaded",totalLoaded:1842,databaseCount:3,selectedEvidence:7,canUseLoaded:true,researcher:false},
};
export default meta;
type Story=StoryObj<typeof SearchWorkspaceHeader>;
export const LoadedRecords:Story={};
export const DatabaseScope:Story={args:{scope:"database"}};
export const Researcher:Story={args:{scope:"database",researcher:true,canUseLoaded:false,totalLoaded:0}};
