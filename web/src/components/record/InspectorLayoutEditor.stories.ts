/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import InspectorLayoutEditor from "./InspectorLayoutEditor.vue";
import { defaultInspectorLayout } from "../../domain/inspectorLayout";
import { onMounted, ref } from "vue";

const meta = {
  title: "Record Workspace/Inspector layout",
  component: InspectorLayoutEditor,
} satisfies Meta<typeof InspectorLayoutEditor>;
export default meta;
type Story = StoryObj<typeof InspectorLayoutEditor>;

export const Default: Story = {
  render: () => ({
    components: { InspectorLayoutEditor },
    setup() {
      const layout = defaultInspectorLayout();
      const editor = ref<{ open: () => void } | null>(null);
      onMounted(() => editor.value?.open());
      return { layout, editor };
    },
    template: `<InspectorLayoutEditor ref="editor" :layout="layout" />`,
  }),
};
