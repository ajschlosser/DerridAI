import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import DashboardView from "../views/DashboardView.vue";
import CorpusView from "../views/CorpusView.vue";
import ResearchView from "../views/ResearchView.vue";
import SearchView from "../views/SearchView.vue";
import RecordView from "../views/RecordView.vue";
import ResponseFaqView from "../views/ResponseFaqView.vue";
import ToolsView from "../views/ToolsView.vue";
import CompareView from "../views/CompareView.vue";
import SystemView from "../views/SystemView.vue";
import SettingsView from "../views/SettingsView.vue";
import UsersView from "../views/UsersView.vue";
import LanguagesView from "../views/LanguagesView.vue";
import RolesView from "../views/RolesView.vue";
import WorksView from "../views/WorksView.vue";
import { useAuthStore } from "../stores/auth";

const routes: RouteRecordRaw[] = [
  { path: "/", name: "home", component: DashboardView, meta: { view: "home", capability: "page.dashboard" } },
  { path: "/records", name: "list", component: CorpusView, meta: { view: "list", capability: "page.records", adminOnly: true } },
  { path: "/record", name: "record", component: RecordView, meta: { view: "record", capability: "page.record", vueNative: true } },
  { path: "/works", name: "works", component: WorksView, meta: { view: "works", capability: "page.works", vueNative: true } },
  { path: "/search", name: "global", component: SearchView, meta: { view: "global", capability: "page.search", vueNative: true } },
  { path: "/annotations", name: "annotations", component: CorpusView, meta: { view: "annotations", capability: "page.annotations" } },
  { path: "/pdf", name: "pdf", component: ToolsView, meta: { view: "pdf", capability: "page.pdf", adminOnly: true } },
  { path: "/compare", name: "compare", component: CompareView, meta: { view: "compare", capability: "page.compare", vueNative: true } },
  { path: "/databases", name: "vector", component: ToolsView, meta: { view: "vector", capability: "page.vector", vueNative: true } },
  { path: "/rag", name: "rag", component: ResearchView, meta: { view: "rag", capability: "page.research" } },
  { path: "/faq", name: "faq", component: ResponseFaqView, meta: { view: "faq", capability: "page.faq", adminOnly: true, vueNative: true } },
  { path: "/response-cache", name: "responsecache", component: ResearchView, meta: { view: "responsecache", capability: "page.response_cache", adminOnly: true } },
  { path: "/providers", name: "providers", component: SystemView, meta: { view: "providers", capability: "page.providers", adminOnly: true } },
  { path: "/settings", name: "config", component: SettingsView, meta: { view: "config", capability: "page.settings", vueNative: true } },
  { path: "/users", name: "users", component: UsersView, meta: { capability: "page.users", adminOnly: true, vueNative: true } },
  { path: "/roles", name: "roles", component: RolesView, meta: { capability: "page.roles", adminOnly: true, vueNative: true } },
  { path: "/languages", name: "languages", component: LanguagesView, meta: { capability: "page.languages", adminOnly: true, vueNative: true } },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router=createRouter({history:createWebHistory(),routes,scrollBehavior:(to,from,savedPosition)=>savedPosition??(to.path===from.path?false:{top:0})});
router.beforeEach(async(to)=>{
  const auth=useAuthStore();
  if(!auth.initialized)await auth.loadStatus();
  if(!auth.user)return true;
  if(to.meta.adminOnly&&!auth.isAdmin)return "/";
  const capability=String(to.meta.capability||"");
  if(capability&&!auth.can(capability))return "/";
  return true;
});
export default router;
