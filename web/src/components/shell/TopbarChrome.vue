<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
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
const storedOperationsMode = localStorage.getItem("derridai.operations-dock-mode");
const operationsDocked = ref(storedOperationsMode !== "floating");
const operationsVisible = ref(false);
const operationsSummary = ref("");
const operationsTone = ref("neutral");
const operationsDropdownOpen = ref(false);
const operationsButton = ref<HTMLButtonElement | null>(null);
let operationsClickTimer: ReturnType<typeof setTimeout> | null = null;
let operationsModeHandler: (() => void) | null = null;
let operationsSummaryHandler: ((event: Event) => void) | null = null;

interface OperationSummaryDetail {
  visible: boolean;
  title: string;
  summary: string;
  percent: number | null;
  tone: string;
  expanded?: boolean;
}

function setOperationsOpen(open: boolean) {
  operationsDropdownOpen.value = open;
  document.documentElement.dataset.operationsDockOpen = open ? "true" : "false";
}

function syncOperationsDockAnchor() {
  if (!operationsDocked.value || !operationsVisible.value) return;
  const button = operationsButton.value;
  if (!button) return;
  const rect = button.getBoundingClientRect();
  document.documentElement.style.setProperty(
    "--operations-dock-anchor-top",
    `${Math.round(rect.bottom + 8)}px`,
  );
  document.documentElement.style.setProperty(
    "--operations-dock-anchor-right",
    `${Math.round(Math.max(8, window.innerWidth - rect.right))}px`,
  );
}

function collapseOperationsForDockedMode() {
  const stack = document.querySelector<HTMLElement>("#operationProgressStack");
  if (!stack || stack.classList.contains("minimized")) return;
  stack.querySelector<HTMLButtonElement>("#operationStackToggle")?.click();
}

function syncOperations(detail?: OperationSummaryDetail) {
  const stack = document.querySelector<HTMLElement>("#operationProgressStack");
  if (detail) {
    const firstDockedAppearance =
      operationsDocked.value && detail.visible && !operationsVisible.value && Boolean(detail.expanded);
    operationsVisible.value = detail.visible;
    operationsSummary.value = [detail.title, detail.summary].filter(Boolean).join(" · ");
    operationsTone.value = detail.tone || "neutral";
    setOperationsOpen(firstDockedAppearance ? false : Boolean(detail.expanded));
    if (firstDockedAppearance) void nextTick(collapseOperationsForDockedMode);
    void nextTick(syncOperationsDockAnchor);
    return;
  }
  operationsVisible.value = Boolean(stack);
  if (!stack) {
    operationsSummary.value = "";
    operationsTone.value = "neutral";
    setOperationsOpen(false);
    return;
  }
  setOperationsOpen(!stack.classList.contains("minimized"));
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
  operationsTone.value = stack.dataset.tone || "neutral";
  void nextTick(syncOperationsDockAnchor);
}

function toggleOperations() {
  if (!operationsDocked.value) return;
  const stack = document.querySelector<HTMLElement>("#operationProgressStack");
  if (!stack) return;
  const nextOpen = !operationsDropdownOpen.value;
  if (nextOpen) syncOperationsDockAnchor();
  setOperationsOpen(nextOpen);
  if (nextOpen !== !stack.classList.contains("minimized")) {
    stack.querySelector<HTMLButtonElement>("#operationStackToggle")?.click();
  }
}

function clearOperationsClickTimer() {
  if (operationsClickTimer === null) return;
  clearTimeout(operationsClickTimer);
  operationsClickTimer = null;
}

function handleOperationsClick(event: MouseEvent) {
  // Keyboard activation has detail=0 and should stay immediate. Pointer clicks are deferred just
  // long enough to distinguish a single click from the double-click gesture that undocks the dock.
  if (event.detail === 0) {
    toggleOperations();
    return;
  }
  if (event.detail > 1) {
    clearOperationsClickTimer();
    return;
  }
  clearOperationsClickTimer();
  operationsClickTimer = setTimeout(() => {
    operationsClickTimer = null;
    toggleOperations();
  }, 300);
}

function setOperationsMode(mode: "floating" | "docked") {
  clearOperationsClickTimer();
  operationsDocked.value = mode === "docked";
  localStorage.setItem("derridai.operations-dock-mode", mode);
  document.documentElement.dataset.operationsDockMode = mode;
  setOperationsOpen(false);
  if (mode === "docked") collapseOperationsForDockedMode();
  void nextTick(syncOperationsDockAnchor);
}

function toggleOperationsMode() {
  setOperationsMode(operationsDocked.value ? "floating" : "docked");
}

function undockOperations(event: MouseEvent) {
  event.preventDefault();
  event.stopPropagation();
  clearOperationsClickTimer();
  setOperationsMode("floating");
}
onMounted(() => {
  document.documentElement.dataset.operationsDockMode = operationsDocked.value
    ? "docked"
    : "floating";
  setOperationsOpen(false);
  operationsModeHandler = toggleOperationsMode;
  globalThis.addEventListener("derridai:operation-mode-toggle", operationsModeHandler);
  operationsSummaryHandler = (event) =>
    syncOperations((event as CustomEvent<OperationSummaryDetail>).detail);
  globalThis.addEventListener("derridai:operation-summary", operationsSummaryHandler);
  window.addEventListener("resize", syncOperationsDockAnchor, { passive: true });
  window.addEventListener("scroll", syncOperationsDockAnchor, { passive: true });
  if (operationsDocked.value) collapseOperationsForDockedMode();
  syncOperations();
});
onBeforeUnmount(() => {
  clearOperationsClickTimer();
  if (operationsModeHandler)
    globalThis.removeEventListener("derridai:operation-mode-toggle", operationsModeHandler);
  if (operationsSummaryHandler)
    globalThis.removeEventListener("derridai:operation-summary", operationsSummaryHandler);
  window.removeEventListener("resize", syncOperationsDockAnchor);
  window.removeEventListener("scroll", syncOperationsDockAnchor);
  document.documentElement.style.removeProperty("--operations-dock-anchor-top");
  document.documentElement.style.removeProperty("--operations-dock-anchor-right");
});
</script>
<template>
  <div class="topbar-chrome">
    <button
      v-if="operationsVisible && operationsDocked"
      ref="operationsButton"
      type="button"
      class="operations-docked-summary"
      :data-tone="operationsTone"
      :aria-label="
        operationsDropdownOpen ? i18n.t('operations.collapse') : i18n.t('operations.expand')
      "
      aria-controls="operationProgressStack"
      :aria-expanded="operationsDropdownOpen"
      @click="handleOperationsClick"
      @dblclick="undockOperations"
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
  min-block-size: 32px;
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
.operations-docked-summary:hover {
  border-color: var(--line-strong);
  background: var(--surface-hover);
}
.operations-docked-summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
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
  background: var(--text-secondary);
}
.operations-docked-summary[data-tone="info"] .operation-dock-dot {
  background: var(--tone-info-fg);
}
.operations-docked-summary[data-tone="success"] .operation-dock-dot {
  background: var(--tone-ok-fg);
}
.operations-docked-summary[data-tone="warning"] .operation-dock-dot {
  background: var(--tone-warn-fg);
}
.operations-docked-summary[data-tone="danger"] .operation-dock-dot {
  background: var(--tone-danger-fg);
}
@media (forced-colors: active) {
  .operations-docked-summary {
    border-color: ButtonText;
  }
  .operations-docked-summary:focus-visible {
    outline-color: Highlight;
  }
  .operation-dock-dot {
    background: ButtonText !important;
  }
}
</style>
