import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiCombobox from "./UiCombobox.vue";
const meta = {
  title: "UI/Combobox",
  component: UiCombobox,
  args: {
    modelValue: "Jacques Derrida",
    label: "Speaker",
    options: ["Jacques Derrida", "Emmanuel Levinas", "Immanuel Kant", "Martin Heidegger"],
    allowCustom: true,
  },
} satisfies Meta<typeof UiCombobox>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const French: Story = { args: { label: "Locuteur", modelValue: "Emmanuel Levinas" } };
