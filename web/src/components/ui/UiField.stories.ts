import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiField from "./UiField.vue";
const meta = {
  title: "Foundations/Forms/Field",
  component: UiField,
  render: (args) => ({
    components: {UiField},
    setup: () => ({args}),
    template: '<UiField v-bind="args"><input class="control" :aria-invalid="Boolean(args.error)" value="Jacques Derrida" /></UiField>',
  }),
  args: {label: "Document author", hint: "Inherited by records unless explicitly overridden."},
} satisfies Meta<typeof UiField>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Invalid: Story = {args: {error: "Enter a document author.", hint: ""}};
export const WithPersistence: Story = {args: {persistence: "Saved in this browser"}};

