import type { Meta, StoryObj } from "@storybook/vue3-vite";
import LanguageWorkspaceHeader from "./LanguageWorkspaceHeader.vue";

const meta = {
  title: "Internationalization/Workspace Header",
  component: LanguageWorkspaceHeader,
  args: {
    languageCount: 4,
    keyCount: 1842,
  },
} satisfies Meta<typeof LanguageWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const PolicyPending: Story = {
  args: {
    languageCount: 2,
    keyCount: 1842,
    policyPendingCount: 2,
  },
};
