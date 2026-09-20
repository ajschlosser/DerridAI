/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import SettingsNav from "./SettingsNav.vue";
import type { SettingsSectionId } from "../../domain/settings";

const items = [
  {id: "workspace" as SettingsSectionId, label: "Workspace and appearance"},
  {id: "language" as SettingsSectionId, label: "Language and accessibility"},
  {id: "research" as SettingsSectionId, label: "Research defaults"},
  {id: "review" as SettingsSectionId, label: "Review and AI behavior"},
  {id: "providers" as SettingsSectionId, label: "Providers and models"},
  {id: "retrieval" as SettingsSectionId, label: "Vector stores and retrieval"},
  {id: "security" as SettingsSectionId, label: "Security, users, and permissions"},
  {id: "system" as SettingsSectionId, label: "System and operations"},
];

const meta = {
  title: "Settings/Navigation",
  component: SettingsNav,
  render: (args) => ({
    components: {SettingsNav},
    setup: () => {
      const section = ref(args.modelValue);
      return {args, section};
    },
    template: `<div style="display:flex;gap:16px;align-items:flex-start">
      <div class="settings-nav" style="max-width:240px"><SettingsNav v-bind="args" v-model="section" /></div>
      <section v-for="item in args.items" :id="'settings-section-' + item.id" :key="item.id" role="tabpanel" :aria-labelledby="'settings-nav-' + item.id" :hidden="section !== item.id">{{ item.label }}</section>
    </div>`,
  }),
  args: {modelValue: "workspace", items, tablistLabel: "Contents"},
} satisfies Meta<typeof SettingsNav>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const French: Story = {
  parameters: {locale: "fr-CA"},
  args: {
    tablistLabel: "Sommaire",
    items: [
      {id: "workspace", label: "Espace de travail et apparence"},
      {id: "language", label: "Langue et accessibilité"},
      {id: "system", label: "Système et opérations"},
    ],
  },
};
