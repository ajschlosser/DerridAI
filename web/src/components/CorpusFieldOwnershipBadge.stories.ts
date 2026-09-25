import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";

const meta: Meta<typeof CorpusFieldOwnershipBadge> = {
  title: "Corpus Builder/Review/Field Ownership Badge",
  component: CorpusFieldOwnershipBadge,
  args: { status: "inherited" },
};

export default meta;
type Story = StoryObj<typeof CorpusFieldOwnershipBadge>;

export const Deterministic: Story = {
  args: { status: "deterministic" },
};

export const Inherited: Story = {
  args: { status: "inherited" },
};

export const ModelInferred: Story = {
  args: { status: "model_inferred" },
};

export const ModelPendingReview: Story = {
  args: { status: "unresolved", method: "llm" },
};

export const ModelInvalid: Story = {
  args: { status: "invalid", method: "llm" },
};

export const HumanConfirmed: Story = {
  args: { status: "human_confirmed" },
};

export const ConfirmedAbsent: Story = {
  args: { status: "confirmed_absent" },
};

export const HumanOverride: Story = {
  args: { status: "human_override" },
};

export const AuditSpotCheck: Story = {
  args: { status: "model_inferred", audit: true },
};

export const Unclassified: Story = {
  args: {},
};

export const NarrowWrappedBadges: Story = {
  args: { status: "model_inferred", audit: true },
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 180px"><story /></div>',
    }),
  ],
};
