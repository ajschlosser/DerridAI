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

export const NAV_SECTION_ORDER = [
  "Research",
  "Corpora",
  "Corpus Management",
  "AI & Automation",
  "System",
] as const;

export const NAV_SECTION_TARGETS: Record<(typeof NAV_SECTION_ORDER)[number], string> = {
  Research: "/rag",
  Corpora: "/search",
  "Corpus Management": "/sources",
  "AI & Automation": "/pipelines",
  System: "/system-data/overview",
};

export const UTILITY_NAV_IDS = new Set(["operations", "help", "config"]);

export const CONTEXTUAL_NAV_IDS = new Set(["record", "relationships"]);

export interface NavigationTarget {
  path: string;
}

export const NAV_TARGETS: Record<string, NavigationTarget> = {
  home: { path: "/" },
  global: { path: "/search" },
  rag: { path: "/rag" },
  faq: { path: "/faq" },
  works: { path: "/works" },
  list: { path: "/records" },
  annotations: { path: "/annotations" },
  semanticmap: { path: "/semantic-map" },
  compare: { path: "/compare" },
  vector: { path: "/databases" },
  pdf: { path: "/corpus-builder" },
  sources: { path: "/sources" },
  responsecache: { path: "/system-data/overview" },
  pipelines: { path: "/pipelines" },
  metadatamemory: { path: "/metadata-memory" },
  providers: { path: "/providers" },
  schemas: { path: "/schemas" },
  config: { path: "/settings/overview" },
  users: { path: "/users" },
  roles: { path: "/roles" },
  languages: { path: "/locale" },
  operations: { path: "/operations" },
  help: { path: "/help" },
};

const ROUTE_NAV_IDS: Record<string, string> = {
  home: "home",
  list: "list",
  record: "record",
  relationships: "record",
  works: "works",
  global: "global",
  annotations: "annotations",
  semanticmap: "semanticmap",
  "corpus-builder": "pdf",
  "source-explorer": "pdf",
  sources: "sources",
  compare: "compare",
  vector: "vector",
  rag: "rag",
  faq: "faq",
  "system-data-overview": "responsecache",
  "system-data-responses": "responsecache",
  "system-data-metadata": "responsecache",
  pipelines: "pipelines",
  "system-data-pipelines": "pipelines",
  "system-data-databases": "responsecache",
  "system-data-advanced": "responsecache",
  providers: "providers",
  schemas: "schemas",
  metadatamemory: "metadatamemory",
  config: "config",
  "settings-section": "config",
  users: "users",
  roles: "users",
  languages: "languages",
  operations: "operations",
  help: "help",
};

export function navIdForRoute(routeName: unknown, fallbackView = ""): string {
  return ROUTE_NAV_IDS[String(routeName || "")] || fallbackView;
}
