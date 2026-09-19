import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CountryFlagPicker from "./CountryFlagPicker.vue";

const meta = {
  title: "Internationalization/Inputs/Country Flag Picker",
  component: CountryFlagPicker,
  args: {
    modelValue: "🇨🇦",
    localeCode: "fr-CA",
    label: "Locale icon",
    help: "Choose a country flag, the neutral globe, or another Unicode symbol.",
  },
  parameters: { layout: "centered" },
} satisfies Meta<typeof CountryFlagPicker>;
export default meta;
type Story = StoryObj<typeof meta>;
export const French: Story = {};
export const UnitedStates: Story = { args: { modelValue: "🇺🇸", localeCode: "en-US" } };
export const Neutral: Story = { args: { modelValue: "🌐", localeCode: "eo" } };
