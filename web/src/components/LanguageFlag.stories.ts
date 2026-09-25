import type { Meta, StoryObj } from "@storybook/vue3-vite";
import LanguageFlag from "./LanguageFlag.vue";
const meta = {
  title: "Internationalization/Visuals/Language Flag",
  component: LanguageFlag,
  args: { code: "en-US", symbol: "🇺🇸", label: "English" },
} satisfies Meta<typeof LanguageFlag>;
export default meta;
type Story = StoryObj<typeof meta>;
export const UnitedStates: Story = {};
export const French: Story = { args: { code: "fr-CA", symbol: "🇨🇦", label: "Français" } };
export const NoFlag: Story = { args: { code: "eo", symbol: "", label: "Esperanto" } };
