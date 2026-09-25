/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SettingsSaveState from "./SettingsSaveState.vue";

const meta = {
  title: "Settings/Save State",
  component: SettingsSaveState,
  args: { status: "saved", label: "Saved" },
} satisfies Meta<typeof SettingsSaveState>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Saved: Story = {};
export const Unsaved: Story = { args: { status: "dirty", label: "Unsaved changes" } };
export const Saving: Story = { args: { status: "saving", label: "Saving" } };
export const Succeeded: Story = { args: { status: "success", label: "Save succeeded" } };
export const Failed: Story = { args: { status: "failed", label: "Save failed" } };
export const ReadOnly: Story = { args: { status: "readonly", label: "Read-only" } };
export const French: Story = {
  parameters: { locale: "fr-CA" },
  args: { status: "dirty", label: "Modifications non enregistrées" },
};
