/* Copyright 2026 Aaron John Schlosser, PhD. */

export const NAV_SECTION_ORDER = [
  "Research",
  "Corpora",
  "Corpus Management",
  "AI & Automation",
  "System",
] as const;

export const UTILITY_NAV_IDS = new Set(["operations", "help", "config"]);

export const CONTEXTUAL_NAV_IDS = new Set(["record", "relationships"]);

export interface NavigationTarget {
  path: string;
  runtimeView?: string;
}

export const NAV_TARGETS: Record<string, NavigationTarget> = {
  home: { path: "/", runtimeView: "home" },
  global: { path: "/search", runtimeView: "global" },
  rag: { path: "/rag", runtimeView: "rag" },
  faq: { path: "/faq", runtimeView: "faq" },
  works: { path: "/works", runtimeView: "works" },
  list: { path: "/records", runtimeView: "list" },
  annotations: { path: "/annotations", runtimeView: "annotations" },
  semanticmap: { path: "/semantic-map", runtimeView: "semanticmap" },
  compare: { path: "/compare", runtimeView: "compare" },
  vector: { path: "/databases", runtimeView: "vector" },
  pdf: { path: "/corpus-builder", runtimeView: "pdf" },
  sources: { path: "/sources" },
  responsecache: { path: "/system-data/overview" },
  pipelines: { path: "/pipelines" },
  metadatamemory: { path: "/metadata-memory" },
  providers: { path: "/providers", runtimeView: "providers" },
  schemas: { path: "/schemas", runtimeView: "schemas" },
  config: { path: "/settings/workspace", runtimeView: "config" },
  users: { path: "/users" },
  roles: { path: "/roles" },
  languages: { path: "/languages" },
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
