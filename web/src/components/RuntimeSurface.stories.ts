import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RuntimeSurface from "./RuntimeSurface.vue";

const meta = {
  title: "Shell/Content Surface",
  component: RuntimeSurface,
  args: { preview: true },
  render: (args) => ({
    components: { RuntimeSurface },
    setup: () => ({ args }),
    template: `<RuntimeSurface v-bind="args"><section class="card" style="padding:20px;min-width:560px"><div class="cardhead"><b>Runtime-rendered feature surface</b></div><p class="note">Vue owns routing and lifecycle; feature renderers mount inside this runtime surface.</p></section></RuntimeSurface>`,
  }),
} satisfies Meta<typeof RuntimeSurface>;

export default meta;
type Story = StoryObj<typeof meta>;
export const RuntimeBoundary: Story = {};
