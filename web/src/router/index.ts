/* Copyright 2026 Aaron John Schlosser, PhD. */
import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("../views/DashboardView.vue"),
    meta: { view: "home", capability: "page.dashboard" },
  },
  {
    path: "/records",
    name: "list",
    component: () => import("../views/RecordsView.vue"),
    meta: { view: "list", capability: "page.records", adminOnly: true, vueNative: true },
  },
  {
    path: "/record",
    name: "record",
    component: () => import("../views/RecordView.vue"),
    meta: { view: "record", capability: "page.record", vueNative: true },
  },
  {
    path: "/works",
    name: "works",
    component: () => import("../views/WorksView.vue"),
    meta: { view: "works", capability: "page.works", vueNative: true },
  },
  {
    path: "/search",
    name: "global",
    component: () => import("../views/SearchView.vue"),
    meta: { view: "global", capability: "page.search", vueNative: true },
  },
  {
    path: "/annotations",
    name: "annotations",
    component: () => import("../views/AnnotationsView.vue"),
    meta: { view: "annotations", capability: "page.annotations", vueNative: true },
  },
  {
    path: "/pdf",
    name: "pdf",
    component: () => import("../views/PdfWorkspaceView.vue"),
    meta: { view: "pdf", capability: "page.pdf", adminOnly: true },
  },
  {
    path: "/compare",
    name: "compare",
    component: () => import("../views/CompareView.vue"),
    meta: { view: "compare", capability: "page.compare", vueNative: true },
  },
  {
    path: "/databases",
    name: "vector",
    component: () => import("../views/VectorStoresView.vue"),
    meta: { view: "vector", capability: "page.vector", vueNative: true },
  },
  {
    path: "/rag",
    name: "rag",
    component: () => import("../views/ResearchView.vue"),
    meta: { view: "rag", capability: "page.research" },
  },
  {
    path: "/faq",
    name: "faq",
    component: () => import("../views/ResponseFaqView.vue"),
    meta: { view: "faq", capability: "page.faq", adminOnly: true, vueNative: true },
  },
  {
    path: "/response-cache",
    name: "responsecache",
    component: () => import("../views/ResponseCacheView.vue"),
    meta: { view: "responsecache", capability: "page.response_cache", adminOnly: true },
  },
  {
    path: "/providers",
    name: "providers",
    component: () => import("../views/ProvidersView.vue"),
    meta: { view: "providers", capability: "page.providers", adminOnly: true, vueNative: true },
  },
  {
    path: "/settings",
    name: "config",
    component: () => import("../views/SettingsView.vue"),
    meta: { view: "config", capability: "page.settings", vueNative: true },
  },
  {
    path: "/users",
    name: "users",
    component: () => import("../views/UsersView.vue"),
    meta: { capability: "page.users", adminOnly: true, vueNative: true },
  },
  {
    path: "/roles",
    name: "roles",
    component: () => import("../views/RolesView.vue"),
    meta: { capability: "page.roles", adminOnly: true, vueNative: true },
  },
  {
    path: "/languages",
    name: "languages",
    component: () => import("../views/LanguagesView.vue"),
    meta: { capability: "page.languages", adminOnly: true, vueNative: true },
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
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
