/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SettingsOverview from "./SettingsOverview.vue";
import type { SettingsSectionId } from "../../domain/settings";

const items = [
  {
    id: "preferences" as SettingsSectionId,
    label: "Preferences",
    description: "Appearance, language, accessibility, and notifications.",
    path: "/settings/preferences",
  },
  {
    id: "research" as SettingsSectionId,
    label: "Research & review",
    description: "Defaults for research output and review execution.",
    path: "/settings/research",
    detail: "Local · Attribution",
  },
  {
    id: "retrieval" as SettingsSectionId,
    label: "Retrieval & indexing",
    description: "Embeddings, retrieval strategy, reranking, and evidence budgets.",
    path: "/settings/retrieval",
  },
  {
    id: "data" as SettingsSectionId,
    label: "Data & storage",
    description: "Retention policy, backup/restore, and data workspaces.",
    path: "/settings/data",
  },
];

const meta = {
  title: "Settings/Overview",
  component: SettingsOverview,
  args: {
    title: "Settings overview",
    description: "Find settings by task and jump to the part of DerridAI that owns the work.",
    navLabel: "Settings categories",
    items,
  },
} satisfies Meta<typeof SettingsOverview>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const French: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    title: "Vue d’ensemble des paramètres",
    description: "Trouvez les paramètres par tâche et ouvrez l’espace de travail qui gère l’opération.",
    navLabel: "Catégories de paramètres",
    items: [
      {
        id: "preferences",
        label: "Préférences",
        description: "Apparence, langue, accessibilité et notifications.",
        path: "/settings/preferences",
      },
      {
        id: "research",
        label: "Recherche et révision",
        description: "Valeurs par défaut de recherche et de révision.",
        path: "/settings/research",
      },
    ],
  },
};
