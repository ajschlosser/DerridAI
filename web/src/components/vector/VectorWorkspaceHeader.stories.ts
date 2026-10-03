/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import VectorWorkspaceHeader from "./VectorWorkspaceHeader.vue";
const health = {
  available: true,
  mode: "embedded" as const,
  path: "/data/chroma",
  host_path_hint: "./data/chroma",
  data_root: "/data",
  url: null,
  tenant: null,
  database: null,
  token_configured: false,
  writable: true,
  heartbeat_ok: true,
  chroma_version: "1.1.0",
  collection_count: 2,
  identity: "Local Chroma · ./data/chroma",
  error: null,
};
const meta = {
  title: "Corpus Data/Workspace Header",
  component: VectorWorkspaceHeader,
  args: { health, collectionCount: 2 },
} satisfies Meta<typeof VectorWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ready: Story = {};
export const Unavailable: Story = {
  args: {
    health: {
      ...health,
      available: false,
      heartbeat_ok: false,
      error: "connection refused",
      identity: "Chroma server · http://chroma:8000",
      mode: "http",
      path: null,
      url: "http://chroma:8000",
    },
  },
};

export const Loading: Story = {
  args: {
    health: null,
    healthLoading: true,
    collectionCount: undefined,
    canCreate: false,
    createDisabledReason: "Loading provider choices…",
  },
};
