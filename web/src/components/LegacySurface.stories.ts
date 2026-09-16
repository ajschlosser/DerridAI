import type { Meta, StoryObj } from "@storybook/vue3-vite";
import LegacySurface from "./LegacySurface.vue";

const meta = {
  title: "Components/LegacySurface",
  component: LegacySurface,
  args: { preview: true },
  render: (args) => ({
    components: { LegacySurface },
    setup: () => ({ args }),
    template: `<LegacySurface v-bind="args"><section class="card" style="padding:20px;min-width:560px"><div class="cardhead"><b>Legacy feature surface</b></div><p class="note">Vue owns routing and lifecycle; feature renderers mount inside this compatibility surface.</p></section></LegacySurface>`,
  }),
} satisfies Meta<typeof LegacySurface>;

export default meta;
type Story = StoryObj<typeof meta>;
export const CompatibilityBoundary: Story = {};
