/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import TopbarChrome from "./TopbarChrome.vue";

const languages = [
  {code: "en-US", name: "English", flag: "🇺🇸"},
  {code: "fr-CA", name: "Français", flag: "🇨🇦"},
];

const meta = {
  title: "Shell/Topbar Chrome",
  component: TopbarChrome,
  render: (args) => ({
    components: {TopbarChrome},
    setup: () => ({args}),
    template: '<div style="display:flex;justify-content:flex-end;padding:12px;background:var(--card)"><TopbarChrome v-bind="args" /></div>',
  }),
  args: {
    username: "aaron",
    role: "admin",
    roleName: "Administrator",
    isAdmin: true,
    canFaq: true,
    canSettings: true,
    fileCount: 2,
    flagged: 3,
    languages,
    locale: "en-US",
  },
} satisfies Meta<typeof TopbarChrome>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Administrator: Story = {};
export const Researcher: Story = {
  args: {role: "researcher", roleName: "Researcher", isAdmin: false, canFaq: false, fileCount: 0, flagged: 0},
};
export const French: Story = {
  parameters: {locale: "fr-CA"},
  args: {locale: "fr-CA"},
};
