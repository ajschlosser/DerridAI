import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ClaimValidationPanel from "./ClaimValidationPanel.vue";

const meta = {
  title: "Record/Claim Validation Panel",
  component: ClaimValidationPanel,
  args: { claimId: "claim-1", status: "unvalidated", record: { record_id: "r1" } },
} satisfies Meta<typeof ClaimValidationPanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Unvalidated: Story = {};
export const Validated: Story = { args: { status: "validated" } };
