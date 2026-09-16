import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RolePermissionMatrix from "../components/RolePermissionMatrix.vue";

const meta = { title: "System/RolePermissionMatrix", component: RolePermissionMatrix, args: { modelValue: ["page.dashboard", "corpus.read"], capabilities: [
  {id:"page.dashboard",category:"Pages",label:"Dashboard",description:"Open the dashboard.",configurable:true},
  {id:"corpus.read",category:"Corpus",label:"Read corpus",description:"Read researcher-safe corpus records.",configurable:true},
  {id:"users.manage",category:"Administration",label:"Manage users",description:"Administrator-only account management.",configurable:false},
] } } satisfies Meta<typeof RolePermissionMatrix>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};

export const ResearchFocused: Story = {
  args: {
    modelValue: ["page.dashboard", "page.research", "rag.run", "corpus.read", "corpus.search"],
    capabilities: [
      {id:"page.dashboard",category:"Pages",label:"Dashboard",description:"Open the dashboard.",configurable:true},
      {id:"page.research",category:"Pages",label:"Research",description:"Open the Research workspace.",configurable:true},
      {id:"rag.run",category:"Research",label:"Run Research",description:"Start evidence-grounded Research jobs.",configurable:true},
      {id:"corpus.read",category:"Corpus",label:"Read corpus",description:"Read protected corpus records.",configurable:true},
      {id:"corpus.search",category:"Corpus",label:"Search corpus",description:"Search protected corpus records.",configurable:true},
      {id:"users.manage",category:"Administration",label:"Manage users",description:"Administrator-only account management.",configurable:false},
    ],
  },
};

export const ReadOnlyCustomRole: Story = {
  args: {
    modelValue: ["page.dashboard", "corpus.read"],
    capabilities: [
      {id:"page.dashboard",category:"Pages",label:"Dashboard",description:"Open the dashboard.",configurable:true},
      {id:"page.research",category:"Pages",label:"Research",description:"Open the Research workspace.",configurable:true},
      {id:"rag.run",category:"Research",label:"Run Research",description:"Start evidence-grounded Research jobs.",configurable:true},
      {id:"corpus.read",category:"Corpus",label:"Read corpus",description:"Read protected corpus records.",configurable:true},
      {id:"annotations.write",category:"Annotations",label:"Write annotations",description:"Create and remove annotations.",configurable:true},
    ],
  },
};
