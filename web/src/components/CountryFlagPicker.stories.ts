import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CountryFlagPicker from "./CountryFlagPicker.vue";

const meta = {
  title: "Localization/CountryFlagPicker",
  component: CountryFlagPicker,
  args: {
    modelValue: "🇨🇦",
    localeCode: "fr-CA",
    label: "Locale icon",
    help: "Choose a country flag or keep the neutral globe.",
  },
} satisfies Meta<typeof CountryFlagPicker>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Neutral: Story = { args: { modelValue: "🌐", localeCode: "eo" } };
