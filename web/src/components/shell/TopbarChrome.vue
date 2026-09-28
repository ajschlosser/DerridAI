<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { LanguageInfo } from "../../api/system";
import { useMatchMedia } from "../../composables/useMatchMedia";
import TopbarAccount from "./TopbarAccount.vue";
import TopbarHelp from "./TopbarHelp.vue";
import TopbarLocale from "./TopbarLocale.vue";
import { useI18nStore } from "../../stores/i18n";

withDefaults(
  defineProps<{
    isAdmin?: boolean;
    canFaq?: boolean;
    canSettings?: boolean;
    username: string;
    role: string;
    roleName?: string;
    languages?: LanguageInfo[];
    locale?: string;
    localeLoading?: boolean;
  }>(),
  {
    isAdmin: false,
    canFaq: false,
    canSettings: true,
    roleName: "",
    languages: () => [],
    locale: "en-US",
    localeLoading: false,
  },
);
const emit = defineEmits<{
  navigate: [view: string];
  logout: [];
  locale: [code: string];
}>();

const compact = useMatchMedia("(max-width: 650px)");
const i18n = useI18nStore();
const helpOpen = ref(false);
const operationsDocked = ref(localStorage.getItem("derridai.operations-dock-mode") === "docked");
const operationsVisible = ref(false);
const operationsSummary = ref("");
let operationsModeHandler: ((event: MouseEvent) => void) | null = null;
let operationsSummaryHandler: ((event: Event) => void) | null = null;

interface OperationSummaryDetail {
  visible: boolean;
  title: string;
  summary: string;
  percent: number | null;
  tone: string;
}

function syncOperations(detail?: OperationSummaryDetail) {
  if (detail) {
    operationsVisible.value = detail.visible;
    operationsSummary.value = [detail.title, detail.summary].filter(Boolean).join(" · ");
    return;
  }
  const stack = document.querySelector<HTMLElement>("#operationProgressStack");
  operationsVisible.value = Boolean(stack);
  if (!stack) {
    operationsSummary.value = "";
    return;
  }
  const title =
    stack
      .querySelector<HTMLElement>(".operation-stack-items .operation-progress b")
      ?.textContent?.trim() ||
    stack.querySelector<HTMLElement>(".operation-dock-title")?.textContent?.trim() ||
    "";
  const count = stack.querySelector<HTMLElement>("#operationStackCount")?.textContent?.trim() || "";
  const bar = stack.querySelector<HTMLElement>(
    ".operation-stack-items [data-progress-bar], .operation-stack-items .operation-progress-track i",
  );
  const percent = bar?.style.width?.trim();
  operationsSummary.value = [title, percent || count].filter(Boolean).join(" · ");
}
function toggleOperations() {
  document.querySelector<HTMLButtonElement>("#operationStackToggle")?.click();
}
function setOperationsMode(mode: "floating" | "docked") {
  operationsDocked.value = mode === "docked";
  localStorage.setItem("derridai.operations-dock-mode", mode);
  document.documentElement.dataset.operationsDockMode = mode;
}
function toggleOperationsMode() {
  setOperationsMode(operationsDocked.value ? "floating" : "docked");
}
onMounted(() => {
  document.documentElement.dataset.operationsDockMode = operationsDocked.value
    ? "docked"
    : "floating";
  operationsModeHandler = (event: MouseEvent) => {
    if ((event.target as HTMLElement | null)?.closest("#operationProgressStack"))
      toggleOperationsMode();
  };
  document.addEventListener("dblclick", operationsModeHandler);
  operationsSummaryHandler = (event) =>
    syncOperations((event as CustomEvent<OperationSummaryDetail>).detail);
  globalThis.addEventListener("derridai:operation-summary", operationsSummaryHandler);
  syncOperations();
});
onBeforeUnmount(() => {
  if (operationsModeHandler) document.removeEventListener("dblclick", operationsModeHandler);
  if (operationsSummaryHandler)
    globalThis.removeEventListener("derridai:operation-summary", operationsSummaryHandler);
});
</script>
<template>
  <div class="topbar-chrome">
    <button
      v-if="operationsVisible && operationsDocked"
      type="button"
      class="operations-docked-summary"
      :aria-label="i18n.t('operations.expand')"
      @click="toggleOperations"
    >
      <span class="operation-dock-dot" aria-hidden="true"></span>
      <span>{{ operationsSummary || i18n.t("operations.title") }}</span>
    </button>
    <TopbarHelp
      v-model:open="helpOpen"
      :show-trigger="!compact"
      :can-faq="canFaq"
      :can-settings="canSettings"
      @navigate="emit('navigate', $event)"
    />
    <TopbarLocale
      v-if="!compact"
      :languages="languages"
      :locale="locale"
      :loading="localeLoading"
      @select="emit('locale', $event)"
    />
    <TopbarAccount
      :username="username"
      :role="role"
      :role-name="roleName"
      :is-admin="isAdmin"
      :compact="compact"
      :can-settings="canSettings"
      :languages="languages"
      :locale="locale"
      :locale-loading="localeLoading"
      @logout="emit('logout')"
      @help="helpOpen = true"
      @navigate="emit('navigate', $event)"
      @locale="emit('locale', $event)"
    />
  </div>
</template>
<style scoped>
.topbar-chrome {
  display: flex;
  align-items: center;
  gap: 8px;
}
.operations-docked-summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-inline-size: min(32vw, 280px);
  padding: 5px 8px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  color: var(--text-secondary);
  background: var(--surface-raised);
  font: inherit;
  font-size: var(--fs-xs);
  cursor: pointer;
}
.operations-docked-summary span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.operation-dock-dot {
  inline-size: 8px;
  block-size: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--tone-info-fg);
}
:global(html[data-operations-dock-mode="docked"] #operationProgressStack) {
  display: none !important;
}
</style>
