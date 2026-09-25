/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiMenu from "./UiMenu.vue";

const items = [
  { id: "open", label: "Open JSONL", icon: "upload" },
  {
    id: "merge",
    label: "Merge files",
    icon: "plus",
    reason: "Load at least two JSONL files to merge them.",
  },
  { id: "export", label: "Export", icon: "download" },
];

const meta = {
  title: "Foundations/Overlays/Menu",
  component: UiMenu,
  args: { label: "Workspace", items, placement: "bottom", align: "end" },
} satisfies Meta<typeof UiMenu>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const IconOnly: Story = {
  args: {
    icon: "help",
    iconOnly: true,
    label: "Help",
    items: [{ id: "guide", label: "Using DerridAI" }],
  },
};
export const LanguageChoices: Story = {
  args: {
    label: "English",
    ariaLabel: "Interface language, English",
    icon: "language",
    items: [
      { id: "en-US", label: "English", checked: true },
      { id: "fr-CA", label: "Français", checked: false },
    ],
  },
};
