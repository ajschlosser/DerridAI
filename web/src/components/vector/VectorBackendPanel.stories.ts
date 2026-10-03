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
import VectorBackendPanel from "./VectorBackendPanel.vue";
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
  collection_count: 1,
  identity: "Local Chroma · ./data/chroma",
  error: null,
};
const meta = {
  title: "Corpus Data/Backend Panel",
  component: VectorBackendPanel,
  args: { health, probing: false, applying: false, probeResult: null, error: "" },
} satisfies Meta<typeof VectorBackendPanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Embedded: Story = {};
export const HttpServer: Story = {
  args: {
    health: {
      ...health,
      mode: "http",
      path: null,
      url: "http://chroma:8000",
      tenant: "default_tenant",
      database: "default_database",
      identity: "Chroma server · http://chroma:8000",
    },
  },
};
