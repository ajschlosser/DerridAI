/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SystemDataStoreCard from "./SystemDataStoreCard.vue";

const meta = {
  title: "System Data/Store Card",
  component: SystemDataStoreCard,
  args: {
    icon: "database",
    title: "Application data",
    detail: "Durable application information such as provider profiles, annotations, languages, and jobs.",
    technical: "system · durable SQLite",
    status: "Available",
    count: "7 tables",
    actionLabel: "Open",
  },
} satisfies Meta<typeof SystemDataStoreCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Available: Story = {};

export const Sensitive: Story = {
  args: {
    icon: "lock",
    title: "Identity and access",
    detail: "Sensitive identity state including users, roles or permissions, sessions, and login security.",
    technical: "auth · sensitive durable SQLite",
    count: "5 tables",
    sensitive: true,
  },
};

export const Unavailable: Story = {
  args: {
    icon: "search",
    title: "Internal vector collections",
    detail: "Application-owned projections for advanced read-only inspection.",
    technical: "system Chroma · derived",
    status: "Unavailable",
    count: "0 collections",
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    title: "Données de l’application",
    detail: "Données durables de l’application, notamment les profils de fournisseurs, les annotations, les langues et les tâches.",
    technical: "system · SQLite durable",
    status: "Disponible",
    count: "7 tables",
    actionLabel: "Ouvrir",
  },
};
