<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";
import { useShellStore, type ShellNavItem } from "./stores/shell";
import { useAuthStore } from "./stores/auth";
import { useI18nStore } from "./stores/i18n";
import UiButton from "./components/ui/UiButton.vue";
import AuthScreen from "./components/AuthScreen.vue";
import CommandSearch from "./components/CommandSearch.vue";
import LanguageFlag from "./components/LanguageFlag.vue";
import AppBuildInfo from "./components/AppBuildInfo.vue";
import AppNotifications from "./components/AppNotifications.vue";
import LlmReviewWorkspace from "./components/LlmReviewWorkspace.vue";
import SidebarBrand from "./components/shell/SidebarBrand.vue";
import SidebarPrimaryNav from "./components/shell/SidebarPrimaryNav.vue";
import SidebarMoreTools from "./components/shell/SidebarMoreTools.vue";
import SidebarStatus from "./components/shell/SidebarStatus.vue";
import type { SidebarNavEntry } from "./components/shell/sidebarNav";
import * as runtime from "./runtime/runtime.js";

const router=useRouter();
const route=useRoute();
const shell=useShellStore();
const auth=useAuthStore();
const i18n=useI18nStore();
const fileInput=ref<HTMLInputElement|null>(null);
const runtimeStarted=ref(false);
const handlingAuthExpiry=ref(false);
const topSearch=ref("");
const commandSearch=ref<InstanceType<typeof CommandSearch>|null>(null);
const MORE_TOOLS_KEY="derridai.ui.moreToolsOpen";
function storedMoreTools():boolean|null{try{const v=localStorage.getItem(MORE_TOOLS_KEY);return v==="1"?true:v==="0"?false:null}catch{return null}}
// Open by default for administrators, but a choice the user has made is remembered.
const moreToolsOpen=ref(storedMoreTools()??false);
const nativeBackPath=ref<string|null>(null);
const nativeForwardPath=ref<string|null>(null);
const s=computed(()=>shell.snapshot);
const currentLocaleInfo=computed(()=>i18n.languages.find(language=>language.code===i18n.locale));
const userInitials=computed(()=>String(auth.user?.username||"U").split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]?.toUpperCase()).join("")||"U");
const pageCapability: Record<string,string> = {home:"page.dashboard",list:"page.records",record:"page.record",works:"page.works",global:"page.search",annotations:"page.annotations",pdf:"page.pdf",compare:"page.compare",vector:"page.vector",rag:"page.research",faq:"page.faq",responsecache:"page.response_cache",providers:"page.providers",config:"page.settings",users:"page.users",languages:"page.languages",roles:"page.roles"};
function canNav(id:string){const capability=pageCapability[id];return !capability||auth.can(capability)}
try{
  const saved=localStorage.getItem("derridai.ui.theme")||"green";
  document.documentElement.dataset.uiTheme=["green","blue","slate"].includes(saved)?saved:"green";
  const scheme=localStorage.getItem("derridai.ui.scheme")||"system";
  const contrast=localStorage.getItem("derridai.ui.contrast")||"system";
  const dark=scheme==="dark"||(scheme!=="light"&&window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.colorScheme=dark?"dark":"light";
  if(contrast==="more"||(contrast==="system"&&window.matchMedia?.("(prefers-contrast: more)").matches))document.documentElement.dataset.contrast="more";
}catch{document.documentElement.dataset.uiTheme="green"}

function languageDisplayName(_code:string,fallback:string){return fallback}
const groupedNav=computed(()=>{
  // Never draw a partial menu: the Vue-side admin items below are appended to the runtime's
  // list, so show nothing until that list exists.
  if(!shell.navReady)return [];
  const groups=shell.groupedNav.map(group=>({section:i18n.t(`section.${group.section.toLowerCase()}`,group.section),items:group.items.filter(item=>canNav(item.id)).map(item=>({...item,label:item.id==="home"?i18n.t("nav.home","Home"):(auth.isResearcher&&item.id==="vector"?i18n.t("research.corpus_search",item.label):i18n.t(`nav.${item.id}`,item.label))}))}));
  if(auth.isAdmin){
    const systemLabel=i18n.t("section.system","System");
    let system=groups.find(group=>group.section===systemLabel);
    if(!system){system={section:systemLabel,items:[]};groups.push(system)}
    if(auth.can("page.users"))system.items.push({id:"users",label:i18n.t("nav.users","Users"),icon:"users",section:"System"} as ShellNavItem);
    if(auth.can("page.roles"))system.items.push({id:"roles",label:i18n.t("nav.roles","Roles & permissions"),icon:"roles",section:"System"} as ShellNavItem);
    if(auth.can("page.languages"))system.items.push({id:"languages",label:i18n.t("language.manage","Manage languages"),icon:"language",section:"System"} as ShellNavItem);
  }
  return groups;
});
const flatNav=computed(()=>groupedNav.value.flatMap(group=>group.items));
const primaryNav=computed(()=>{
  const order=["home","global","works","record","rag","annotations","config"];
  const byId=new Map(flatNav.value.map(item=>[item.id,item]));
  return order.map(id=>byId.get(id)).filter((item):item is ShellNavItem=>Boolean(item));
});
const utilityNav=computed(()=>{const ids=new Set(primaryNav.value.map(item=>item.id));return flatNav.value.filter(item=>!ids.has(item.id))});
const primaryNavItems=computed<SidebarNavEntry[]>(()=>{
  const items:SidebarNavEntry[]=primaryNav.value.map(item=>({id:item.id,label:item.label,icon:item.icon,active:isNavActive(item),disabledReason:item.disabledReason}));
  if(auth.isAdmin)items.push({id:"operations",label:i18n.t("ui.operations","Operations"),icon:"history",active:operationsActive.value});
  return items;
});
const utilityNavItems=computed<SidebarNavEntry[]>(()=>utilityNav.value.map(item=>({id:item.id,label:item.label,icon:item.icon,active:isNavActive(item),disabledReason:item.disabledReason})));
const breadcrumbTitle=computed(()=>route.name==="users"?i18n.t("nav.users","Users"):route.name==="roles"?i18n.t("nav.roles","Roles & permissions"):route.name==="languages"?i18n.t("language.manage","Manage languages"):route.name==="config"?i18n.t("nav.config","Settings"):route.name==="compare"?i18n.t("nav.compare","Compare"):route.name==="list"?i18n.t("nav.records","Records"):s.value.context.title||i18n.t("nav.home","Home"));
const breadcrumbMeta=computed(()=>route.name==="config"?i18n.t("settings.page_help_short","Workspace, research defaults, and operations"):route.name==="compare"?i18n.t("context.compare.meta","Inspect field and text differences"):route.name==="list"?i18n.t("context.list.meta","Open a JSONL file"):["users","roles","languages"].includes(String(route.name||""))?"":s.value.context.meta);
const canBreadcrumbBack=computed(()=>Boolean(nativeBackPath.value)||s.value.canGoBack);
const canBreadcrumbForward=computed(()=>Boolean(nativeForwardPath.value)||s.value.canGoForward);
const breadcrumbBackLabel=computed(()=>nativeBackPath.value?i18n.t("ui.back","Back"):s.value.backLabel);
const breadcrumbForwardLabel=computed(()=>nativeForwardPath.value?i18n.t("ui.forward","Forward"):s.value.forwardLabel);

function invoke(action:()=>unknown){return action()}
function chooseFiles(){if(auth.isAdmin)fileInput.value?.click()}
function onFiles(event:Event){if(!auth.isAdmin)return;const input=event.target as HTMLInputElement;if(input.files?.length)runtime.triggerImport(input.files);input.value=""}
function navigateNative(path:string,runtimeView?:string){
  const current=router.currentRoute.value.fullPath;
  if(current===path)return;
  nativeBackPath.value=current;
  nativeForwardPath.value=null;
  if(runtimeView){
    // Keep runtime state and the native route/query in lockstep. Some
    // native workspaces (notably Corpus Builder / PDF Explorer) use query
    // parameters to select a tab or a durable background build.
    runtime.navigateView(runtimeView,path);
    return;
  }
  void router.push(path);
}
function goBreadcrumbBack(){
  if(nativeBackPath.value){
    const target=nativeBackPath.value;
    nativeForwardPath.value=router.currentRoute.value.fullPath;
    nativeBackPath.value=null;
    void router.push(target);
    return;
  }
  runtime.triggerBack();
}
function goBreadcrumbForward(){
  if(nativeForwardPath.value){
    const target=nativeForwardPath.value;
    nativeBackPath.value=router.currentRoute.value.fullPath;
    nativeForwardPath.value=null;
    void router.push(target);
    return;
  }
  runtime.triggerForward();
}
// Operations is a panel shown over the dashboard, not a route, so track it
// here to highlight the right nav item instead of "Home".
const operationsActive=ref(false);
// Navigating to Operations itself changes the route, so re-derive from whether the
// panel is actually on screen after the new route settles.
watch(()=>route.fullPath,()=>{window.setTimeout(()=>{operationsActive.value=Boolean(document.querySelector("#operationsPanel"))},250)});
function navigate(view:string){
  operationsActive.value=view==="operations";
  // Do not gate Research from the shell's cached database snapshot. ResearchView
  // refreshes the authoritative store list before deciding whether a redirect is
  // needed. This avoids a false “create a database” redirect immediately after
  // a collection is created or restored.
  if(view==="users"){navigateNative("/users");return}
  if(view==="languages"){navigateNative("/languages");return}
  if(view==="roles"){navigateNative("/roles");return}
  if(view==="operations"){runtime.triggerOperations();window.setTimeout(()=>document.querySelector("#operationsPanel")?.scrollIntoView({behavior:"smooth",block:"start"}),80);return}
  nativeBackPath.value=null;nativeForwardPath.value=null;
  runtime.navigateView(view)
}
function isNavActive(item:ShellNavItem){if(operationsActive.value&&item.id==="home")return false;if(item.id==="users")return route.name==="users";if(item.id==="roles")return route.name==="roles";if(item.id==="languages")return route.name==="languages";return !["users","roles","languages"].includes(String(route.name||""))&&s.value.view===item.id}
function closeFile(event:MouseEvent,id:string){event.stopPropagation();if(auth.isAdmin)runtime.closeWorkspaceFile(id)}
function submitTopSearch(){const query=topSearch.value.trim();if(!query)return;runtime.state.globalSearch=query;runtime.state.storeQuery=query;runtime.state.globalPage=1;runtime.state.storeSearchResults=[];runtime.state.globalSearchMode="traditional";runtime.navigateView("global")}
function openHelp(){runtime.navigateView("faq")}
function onMoreToolsToggle(open:boolean){
  // A programmatic change already matches the model; only a user toggle differs from it.
  if(open===moreToolsOpen.value)return;
  moreToolsOpen.value=open;
  try{localStorage.setItem(MORE_TOOLS_KEY,open?"1":"0")}catch{/* preference is optional */}
}
async function startRuntime(){
  if(!auth.user||runtimeStarted.value)return;
  runtimeStarted.value=true;
  runtime.setUserContext(auth.user);
  runtime.setShellRefreshHook(()=>shell.sync());
  // Menu membership needs only the user and static config, so publish it now rather than
  // after the (potentially slow) bootstrap below finishes its first full snapshot.
  shell.syncNav();
  runtime.setUrlSyncHook((href:string,options:{replace?:boolean})=>{
    // Runtime rendering requests URL synchronization frequently. Never send
    // Vue Router to the location it already owns.
    const target=router.resolve(href).fullPath;
    if(router.currentRoute.value.fullPath===target)return;
    const method=options?.replace?router.replace:router.push;
    void method(target).catch(()=>undefined);
  });
  try{
    const requiredCapability=String(route.meta.capability||'');
    if(requiredCapability&&!auth.can(requiredCapability))await router.replace('/');
    if(!i18n.languages.length)await i18n.initialize();
    await runtime.bootstrapRuntime();
    shell.sync();
    shell.ready=true;
  }catch(error){
    runtimeStarted.value=false;
    console.error('DerridAI runtime bootstrap failed',error);
    throw error;
  }
}

async function logout(){
  runtime.pauseRuntime();
  runtimeStarted.value=false;
  await auth.logout();
  await router.replace("/");
}
async function handleAuthExpired(){
  // Ignore 401s from pre-auth/bootstrap requests. There is no session to expire.
  if(handlingAuthExpiry.value||!auth.user)return;
  handlingAuthExpiry.value=true;
  try{
    runtime.pauseRuntime();
    runtimeStarted.value=false;
    auth.expireSession(i18n.t("auth.session_expired","Your session expired. Sign in again."));
    if(router.currentRoute.value.path!=="/")await router.replace("/");
  }finally{
    // Keep one microtask between a burst of 401 responses and accepting a new
    // expiry event from a future authenticated session.
    queueMicrotask(()=>{handlingAuthExpiry.value=false});
  }
}

onMounted(async()=>{
  window.addEventListener("derridai-auth-expired",()=>{void handleAuthExpired()});
  window.addEventListener("derridai:navigate-native",((event:Event)=>{const detail=(event as CustomEvent<{path?:string;runtimeView?:string}>).detail||{};if(detail.path)navigateNative(detail.path,detail.runtimeView)}) as EventListener);
  window.addEventListener("keydown",(event:KeyboardEvent)=>{if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==="k"){event.preventDefault();commandSearch.value?.focus()}});
  // Authentication must be resolved before protected runtime bootstrap. The
  // read-only language endpoints are public so the sign-in screen can still be
  // fully localized.
  if(!auth.initialized)await auth.loadStatus();
  if(!i18n.languages.length)await i18n.initialize();
  await startRuntime();
});
watch(()=>auth.isAdmin,value=>{if(storedMoreTools()===null)moreToolsOpen.value=Boolean(value)},{immediate:true});
watch(()=>auth.user?.id,(id)=>{
  if(!id){runtime.pauseRuntime();runtimeStarted.value=false;shell.resetNav();return}
  void startRuntime()
});
</script>

<template>
  <div v-if="!auth.initialized" class="auth-loading">{{ i18n.t("ui.loading_derridai","Loading DerridAI…") }}</div>
  <AuthScreen v-else-if="!auth.user" />
  <div v-else class="app-shell app-shell-modern" :class="{'sidebar-collapsed':s.sidebarCollapsed}">
    <a class="skip-link" href="#appContent">{{ i18n.t("ui.skip_to_content","Skip to main content") }}</a>
    <aside class="sidebar shell-sidebar">
      <SidebarBrand :collapsed="s.sidebarCollapsed" @navigate-home="navigate('home')" @toggle="runtime.toggleSidebar()" />
      <SidebarPrimaryNav :items="primaryNavItems" @navigate="navigate" />
      <SidebarMoreTools v-if="utilityNavItems.length&&!s.sidebarCollapsed" :items="utilityNavItems" :open="moreToolsOpen" @update:open="onMoreToolsToggle" @navigate="navigate" />
      <div class="sidebar-spacer"></div>
      <SidebarStatus
        v-if="!s.sidebarCollapsed"
        :is-admin="auth.isAdmin"
        :has-corpus-db="s.hasCorpusDb"
        :total-loaded="s.totalLoaded"
        :corpus-store-count="s.corpusStoreCount"
        :active-store="s.activeStore"
        :db-records="s.dbRecords"
        :selected-evidence-count="s.selectedEvidenceCount"
      />
    </aside>

    <section class="workspace shell-workspace">
      <header class="topbar shell-topbar"><CommandSearch ref="commandSearch" v-model="topSearch" :placeholder="i18n.t('ui.global_search_placeholder','Search the corpus, works, concepts, or annotations…')" @submit="submitTopSearch"/><div class="shell-top-actions">
        <details v-if="auth.isAdmin" class="shell-actions-menu"><summary>{{i18n.t('ui.admin_actions','Actions')}}</summary><div class="shell-actions-popover"><input id="fileInput" ref="fileInput" type="file" accept=".jsonl,.ndjson,.json" multiple hidden @change="onFiles"><UiButton :label="i18n.t('ui.open_jsonl','Open JSONL')" icon="upload" @click="chooseFiles"/><UiButton :label="i18n.t('ui.merge_tabs','Merge tabs')" icon="plus" :disabled="s.files.length<2" :disabled-reason="i18n.t('ui.need_two_tabs_merge','Load at least two JSONL tabs to merge them.')" @click="invoke(runtime.triggerMerge)"/><UiButton :label="i18n.t('ui.create_subset','Create subset')" icon="filter" :disabled="!s.files.length" :disabled-reason="i18n.t('ui.need_records_subset','Load JSONL records before creating a subset.')" @click="invoke(runtime.triggerSubset)"/><UiButton :label="i18n.t('ui.bulk_edit','Bulk edit field')" icon="edit" :disabled="!s.files.length" :disabled-reason="i18n.t('ui.need_records_bulk_edit','Load JSONL records before bulk editing.')" @click="invoke(runtime.triggerBulkEdit)"/><UiButton :label="i18n.t('ui.clean_ocr','Clean OCR Artifacts')" icon="broom" :disabled="!s.files.length" :disabled-reason="i18n.t('ui.need_records_ocr','Load JSONL records before cleaning OCR artifacts.')" @click="invoke(runtime.triggerOcrClean)"/><UiButton v-if="s.flagged" :label="i18n.t('ui.review_flagged','Review flagged')" icon="spark" :count="s.flagged" @click="invoke(runtime.triggerReviewFlagged)"/><UiButton :label="i18n.t('ui.operations','Operations')" icon="history" :count="s.activeJobs" @click="invoke(runtime.triggerOperations)"/><UiButton :label="i18n.t('ui.export','Export')" icon="download" :disabled="!s.files.length" :disabled-reason="i18n.t('ui.need_records_export','Load JSONL records before exporting.')" @click="invoke(runtime.triggerExport)"/></div></details>
        <button class="shell-icon-button" type="button" :title="i18n.t('nav.faq','Help')" @click="openHelp">?</button>
        <div class="language-switcher shell-language-switcher"><LanguageFlag :code="i18n.locale" :symbol="currentLocaleInfo?.flag" :label="currentLocaleInfo?.name" size="small"/><select id="localePicker" :aria-label="i18n.t('dashboard.interface_language','Interface language')" :value="i18n.locale" :disabled="i18n.loading" @change="i18n.setLocale(($event.target as HTMLSelectElement).value)"><option v-for="language in i18n.languages" :key="language.code" :value="language.code">{{languageDisplayName(language.code,language.name)}}</option></select></div>
        <details class="shell-user-menu"><summary><span class="shell-avatar">{{userInitials}}</span><span class="shell-user-copy"><b>{{auth.user.username}}</b><small>{{auth.user.role_name||auth.user.role}}</small></span><span>⌄</span></summary><div class="shell-user-popover"><AppBuildInfo compact :show-commit="auth.isAdmin"/><button class="btn" type="button" @click="logout">{{i18n.t('ui.sign_out','Sign out')}}</button></div></details>
      </div></header>
      <nav class="vue-breadcrumb shell-breadcrumb" :aria-label="i18n.t('ui.navigation_history','Navigation history')"><div class="breadcrumb-nav"><button class="breadcrumb-nav-button" type="button" :disabled="!canBreadcrumbBack" :title="breadcrumbBackLabel" @click="goBreadcrumbBack" :aria-label="i18n.t('ui.back','Back')"><span aria-hidden="true">←</span><span class="breadcrumb-button-label">{{i18n.t('ui.back','Back')}}</span></button><button class="breadcrumb-nav-button" type="button" :disabled="!canBreadcrumbForward" :title="breadcrumbForwardLabel" @click="goBreadcrumbForward" :aria-label="i18n.t('ui.forward','Forward')"><span class="breadcrumb-button-label">{{i18n.t('ui.forward','Forward')}}</span><span aria-hidden="true">→</span></button></div><div class="vue-breadcrumb-path"><span>DerridAI</span><b aria-hidden="true">›</b><strong>{{breadcrumbTitle}}</strong><span v-if="breadcrumbMeta" class="shell-breadcrumb-meta">{{breadcrumbMeta}}</span></div></nav>
      <div v-if="auth.isAdmin&&s.files.length" class="file-tabs shell-file-tabs"><div v-for="file in s.files" :key="file.id" class="tab" :class="{active:file.active}" @click="runtime.activateFile(file.id)"><span v-if="file.dirty" class="dot"></span><span class="tn">{{file.name}}</span><span class="badge">{{file.count.toLocaleString(i18n.locale)}}</span><button class="x" :title="i18n.t('ui.close_file','Close file')" @click="closeFile($event,file.id)">×</button></div></div>
      <div id="appContent" class="app-content-region" tabindex="-1"><RouterView/></div>
    </section>
  </div>
  <LlmReviewWorkspace />
  <AppNotifications />
</template>
