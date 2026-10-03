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

import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "../stores/auth";

const systemDataRoute = (
  path: string,
  name: string,
  titleKey: string,
  titleFallback: string,
): RouteRecordRaw => ({
  path,
  name,
  component: () => import("../views/SystemDataView.vue"),
  meta: {
    view: "systemdata",
    navId: "responsecache",
    navSection: "System",
    titleKey,
    titleFallback,
    breadcrumbParentKey: "runtime.system_data",
    breadcrumbParentFallback: "System Data",
    capability: "page.response_cache",
    adminOnly: true,
    vueNative: true,
  },
});

export const APP_ROUTES: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("../views/DashboardView.vue"),
    meta: {
      view: "home",
      navId: "home",
      navSection: "Overview",
      titleKey: "nav.home",
      titleFallback: "Home",
      capability: "page.dashboard",
    },
  },
  {
    path: "/search",
    name: "global",
    component: () => import("../views/SearchView.vue"),
    meta: {
      view: "global",
      navId: "global",
      navSection: "Corpora",
      titleKey: "nav.search",
      titleFallback: "Search",
      capability: "page.search",
      vueNative: true,
    },
  },
  {
    path: "/rag",
    name: "rag",
    component: () => import("../views/ResearchView.vue"),
    meta: {
      view: "rag",
      navId: "rag",
      navSection: "Research",
      titleKey: "nav.rag",
      titleFallback: "Research",
      capability: "page.research",
    },
  },
  {
    path: "/faq",
    name: "faq",
    component: () => import("../views/ResponseFaqView.vue"),
    meta: {
      view: "faq",
      navId: "faq",
      navSection: "Research",
      titleKey: "nav.faq",
      titleFallback: "Response Library",
      capability: "page.faq",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/works",
    name: "works",
    component: () => import("../views/WorksView.vue"),
    meta: {
      view: "works",
      navId: "works",
      navSection: "Corpora",
      titleKey: "nav.works",
      titleFallback: "Works",
      capability: "page.works",
      vueNative: true,
    },
  },
  {
    path: "/records",
    name: "list",
    component: () => import("../views/RecordsView.vue"),
    meta: {
      view: "list",
      navId: "list",
      navSection: "Corpora",
      titleKey: "nav.records",
      titleFallback: "Records",
      capability: "page.records",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/record",
    name: "record",
    component: () => import("../views/RecordView.vue"),
    meta: {
      view: "record",
      navId: "record",
      navSection: "Corpora",
      titleKey: "nav.record",
      titleFallback: "Record View",
      capability: "page.record",
      breadcrumbParentKey: "nav.records",
      breadcrumbParentFallback: "Records",
      breadcrumbParentPath: "/records",
      vueNative: true,
      contextual: true,
    },
  },
  {
    path: "/relationships",
    name: "relationships",
    component: () => import("../views/RelationshipBrowserView.vue"),
    meta: {
      view: "relationships",
      navId: "record",
      navSection: "Corpora",
      titleKey: "relationships.title",
      titleFallback: "Relationships",
      capability: "page.record",
      breadcrumbParentKey: "nav.records",
      breadcrumbParentFallback: "Records",
      breadcrumbParentPath: "/records",
      vueNative: true,
      contextual: true,
    },
  },
  {
    path: "/annotations",
    name: "annotations",
    component: () => import("../views/AnnotationsView.vue"),
    meta: {
      view: "annotations",
      navId: "annotations",
      navSection: "Corpora",
      titleKey: "nav.annotations",
      titleFallback: "Annotations",
      capability: "page.annotations",
      vueNative: true,
    },
  },
  {
    path: "/semantic-map",
    name: "semanticmap",
    component: () => import("../views/SemanticMapView.vue"),
    meta: {
      view: "semanticmap",
      navId: "semanticmap",
      navSection: "Corpora",
      titleKey: "nav.semantic_map",
      titleFallback: "Semantic map",
      capability: "page.semantic_map",
      vueNative: true,
    },
  },
  {
    path: "/compare",
    name: "compare",
    component: () => import("../views/CompareView.vue"),
    meta: {
      view: "compare",
      navId: "compare",
      navSection: "Corpora",
      titleKey: "nav.compare",
      titleFallback: "Compare",
      capability: "page.compare",
      vueNative: true,
    },
  },
  {
    path: "/databases",
    name: "vector",
    component: () => import("../views/VectorStoresView.vue"),
    meta: {
      view: "vector",
      navId: "vector",
      navSection: "Corpus Management",
      titleKey: "nav.vector",
      titleFallback: "Corpus Data",
      capability: "page.vector",
      vueNative: true,
    },
  },
  {
    path: "/corpus-builder",
    name: "corpus-builder",
    component: () => import("../views/PdfWorkspaceView.vue"),
    meta: {
      view: "pdf",
      navId: "pdf",
      navSection: "Corpus Management",
      titleKey: "pdf_workspace.builder",
      titleFallback: "Corpus Builder",
      pdfMode: "builder",
      capability: "page.pdf",
      adminOnly: true,
    },
  },
  {
    path: "/source-explorer",
    name: "source-explorer",
    component: () => import("../views/PdfWorkspaceView.vue"),
    meta: {
      view: "pdf",
      navId: "pdf",
      navSection: "Corpus Management",
      titleKey: "pdf_workspace.explorer",
      titleFallback: "Source Explorer",
      breadcrumbParentKey: "pdf_workspace.builder",
      breadcrumbParentFallback: "Corpus Builder",
      breadcrumbParentPath: "/corpus-builder",
      pdfMode: "explorer",
      capability: "page.pdf",
      adminOnly: true,
    },
  },
  {
    path: "/pdf",
    redirect: (to) => {
      const query = { ...to.query };
      const explorer = query.mode === "explorer";
      delete query.mode;
      return { name: explorer ? "source-explorer" : "corpus-builder", query };
    },
  },
  {
    path: "/sources",
    name: "sources",
    component: () => import("../views/SourcesView.vue"),
    meta: {
      view: "sources",
      navId: "sources",
      navSection: "Corpus Management",
      titleKey: "sources.title",
      titleFallback: "Sources",
      capability: "page.pdf",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/response-cache",
    redirect: (to) => ({ name: "system-data-responses", query: to.query }),
  },
  {
    path: "/system-data",
    redirect: (to) => {
      const requested = String(to.query.section || "overview");
      const allowed = new Set([
        "overview",
        "responses",
        "metadata",
        "pipelines",
        "databases",
        "advanced",
      ]);
      const section = allowed.has(requested) ? requested : "overview";
      const query = { ...to.query };
      delete query.section;
      if (section === "pipelines") return { name: "pipelines", query };
      return { name: `system-data-${section}`, query };
    },
  },
  systemDataRoute(
    "/system-data/overview",
    "system-data-overview",
    "runtime.system_overview",
    "Overview",
  ),
  systemDataRoute(
    "/system-data/responses",
    "system-data-responses",
    "runtime.system_responses",
    "Responses",
  ),
  systemDataRoute(
    "/system-data/metadata",
    "system-data-metadata",
    "runtime.system_metadata_examples",
    "Metadata examples",
  ),
  {
    path: "/system-data/pipelines",
    redirect: (to) => ({ name: "pipelines", query: to.query }),
  },
  systemDataRoute(
    "/system-data/databases",
    "system-data-databases",
    "runtime.system_databases",
    "Databases",
  ),
  systemDataRoute(
    "/system-data/advanced",
    "system-data-advanced",
    "runtime.system_advanced",
    "Advanced",
  ),
  {
    path: "/pipelines",
    name: "pipelines",
    component: () => import("../views/PipelineStudioView.vue"),
    meta: {
      view: "responsecache",
      navId: "pipelines",
      navSection: "AI & Automation",
      titleKey: "pipelines.title",
      titleFallback: "Pipeline Studio",
      capability: "page.response_cache",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/metadata-memory",
    name: "metadatamemory",
    component: () => import("../views/MetadataMemoryView.vue"),
    meta: {
      view: "metadatamemory",
      navId: "metadatamemory",
      navSection: "AI & Automation",
      titleKey: "metadata_memory.title",
      titleFallback: "Metadata memory",
      capability: "page.response_cache",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/providers",
    name: "providers",
    component: () => import("../views/ProvidersView.vue"),
    meta: {
      view: "providers",
      navId: "providers",
      navSection: "AI & Automation",
      titleKey: "nav.providers",
      titleFallback: "LLM Providers",
      capability: "page.providers",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/schemas",
    name: "schemas",
    component: () => import("../views/MetadataSchemasView.vue"),
    meta: {
      view: "schemas",
      navId: "schemas",
      navSection: "Corpus Management",
      titleKey: "nav.schemas",
      titleFallback: "Metadata schemas",
      capability: "page.schemas",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/settings",
    redirect: (to) => {
      const section = String(to.query.section || "overview");
      const query = { ...to.query };
      delete query.section;
      return { name: "settings-section", params: { section }, query };
    },
  },
  {
    path: "/settings/:section",
    name: "settings-section",
    component: () => import("../views/SettingsView.vue"),
    meta: {
      view: "config",
      navId: "config",
      navSection: "System",
      titleKey: "nav.config",
      titleFallback: "Settings",
      capability: "page.settings",
      vueNative: true,
    },
  },
  {
    path: "/users",
    name: "users",
    component: () => import("../views/UsersView.vue"),
    meta: {
      view: "users",
      navId: "users",
      navSection: "System",
      titleKey: "nav.users",
      titleFallback: "Users & roles",
      capability: "page.users",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/roles",
    name: "roles",
    component: () => import("../views/RolesView.vue"),
    meta: {
      view: "roles",
      navId: "roles",
      navSection: "System",
      titleKey: "nav.roles",
      titleFallback: "Roles & permissions",
      breadcrumbParentKey: "nav.users",
      breadcrumbParentFallback: "Users & roles",
      breadcrumbParentPath: "/users",
      capability: "page.roles",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/languages",
    name: "languages",
    component: () => import("../views/LanguagesView.vue"),
    meta: {
      view: "languages",
      navId: "languages",
      navSection: "System",
      titleKey: "language.manage",
      titleFallback: "Languages",
      capability: "page.languages",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/operations",
    name: "operations",
    component: () => import("../views/OperationsView.vue"),
    meta: {
      view: "operations",
      navId: "operations",
      titleKey: "ui.operations",
      titleFallback: "Operations",
      adminOnly: true,
      vueNative: true,
    },
  },
  {
    path: "/help",
    name: "help",
    component: () => import("../views/HelpCenterView.vue"),
    meta: {
      view: "help",
      navId: "help",
      titleKey: "help.title",
      titleFallback: "Help center",
      vueNative: true,
    },
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes: APP_ROUTES,
  scrollBehavior: (to, from, savedPosition) =>
    savedPosition ?? (to.path === from.path ? false : { top: 0 }),
});
router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.initialized) await auth.loadStatus();
  if (!auth.user) return true;
  if (to.meta.adminOnly && !auth.isAdmin) return "/";
  const capability = String(to.meta.capability || "");
  if (capability && !auth.can(capability)) return "/";
  return true;
});
export default router;
