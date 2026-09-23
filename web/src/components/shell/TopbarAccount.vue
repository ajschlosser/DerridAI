<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId } from "vue";
import AppBuildInfo from "../AppBuildInfo.vue";
import AppIcon from "../AppIcon.vue";
import UiButton from "../ui/UiButton.vue";
import { useI18nStore } from "../../stores/i18n";
import { roleLabel, userInitials } from "../../domain/account";

const props = withDefaults(
  defineProps<{
    username: string;
    role: string;
    roleName?: string;
    isAdmin?: boolean;
    compact?: boolean;
    canSettings?: boolean;
    languages?: { code: string; name: string }[];
    locale?: string;
    localeLoading?: boolean;
  }>(),
  {
    roleName: "",
    isAdmin: false,
    compact: false,
    canSettings: true,
    languages: () => [],
    locale: "",
    localeLoading: false,
  },
);
const emit = defineEmits<{
  logout: [];
  help: [];
  navigate: [view: string];
  locale: [code: string];
}>();

const i18n = useI18nStore();
const open = ref(false);
const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLButtonElement | null>(null);
const panel = ref<HTMLElement | null>(null);
const dialogId = `${useId()}-account`;
const titleId = `${dialogId}-title`;
const heading = ref<HTMLElement | null>(null);
const initials = () => userInitials(props.username);
const translatedRole = () => roleLabel(props.role, props.roleName, i18n.t);
const accountName = () =>
  i18n.tf("ui.account_menu_named", { name: props.username });

function focusable(): HTMLElement[] {
  if (!panel.value) return [];
  return Array.from(
    panel.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])',
    ),
  ).filter((node) => node.offsetParent !== null);
}
function outside(event: Event) {
  if (root.value && !root.value.contains(event.target as Node)) close(false);
}
async function show() {
  open.value = true;
  document.addEventListener("pointerdown", outside, true);
  await nextTick();
  (heading.value || focusable()[0])?.focus({ preventScroll: true });
}
function close(returnFocus: boolean) {
  if (!open.value) return;
  open.value = false;
  document.removeEventListener("pointerdown", outside, true);
  if (returnFocus) trigger.value?.focus();
}
function toggle() {
  if (open.value) close(true);
  else void show();
}
function onTriggerKey(event: KeyboardEvent) {
  if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    void show();
  }
}
function onPanelKey(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    close(true);
    return;
  }
  if (event.key !== "Tab") return;
  const nodes = focusable();
  if (!nodes.length) {
    event.preventDefault();
    return;
  }
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
function go(view: string) {
  close(true);
  emit("navigate", view);
}
function setLocale(code: string) {
  emit("locale", code);
}
function openHelp() {
  close(false);
  emit("help");
}
function signOut() {
  close(false);
  emit("logout");
}
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside, true));
</script>
<template>
  <div ref="root" class="topbar-account">
    <button
      ref="trigger"
      type="button"
      class="topbar-account-trigger"
      aria-haspopup="dialog"
      :aria-expanded="open"
      :aria-controls="open ? dialogId : undefined"
      :aria-label="accountName()"
      @click="toggle"
      @keydown="onTriggerKey"
    >
      <span class="shell-avatar" aria-hidden="true">{{ initials() }}</span>
      <span v-if="!compact" class="topbar-account-copy">
        <b>{{ username }}</b>
        <small>{{ translatedRole() }}</small>
      </span>
      <AppIcon v-if="!compact" name="chevron-down" aria-hidden="true" />
    </button>
    <div
      v-if="open"
      :id="dialogId"
      ref="panel"
      class="topbar-account-panel"
      role="dialog"
      :aria-labelledby="titleId"
      @keydown="onPanelKey"
    >
      <h2 :id="titleId" ref="heading" class="sr-only" tabindex="-1">{{ i18n.t("ui.account_menu") }}</h2>
      <div class="topbar-account-identity">
        <span class="shell-avatar" aria-hidden="true">{{ initials() }}</span>
        <div>
          <b>{{ username }}</b>
          <small>{{ translatedRole() }}</small>
        </div>
      </div>
      <AppBuildInfo compact :show-commit="isAdmin" />
      <div class="topbar-account-actions">
        <UiButton
          v-if="canSettings"
          :label="i18n.t('nav.config')"
          icon="gear"
          @click="go('config')"
        />
        <UiButton
          v-if="compact"
          :label="i18n.t('ui.help')"
          icon="help"
          @click="openHelp"
        />
        <div v-if="compact && languages.length" class="topbar-account-locale">
          <p id="account-locale-label">{{ i18n.t("ui.language_menu") }}</p>
          <div role="radiogroup" aria-labelledby="account-locale-label">
            <label v-for="language in languages" :key="language.code">
              <input
                type="radio"
                name="account-locale"
                :value="language.code"
                :checked="language.code === locale"
                :disabled="localeLoading"
                @change="setLocale(language.code)"
              />
              <span>{{ language.name }}</span>
            </label>
          </div>
        </div>
        <UiButton variant="danger" :label="i18n.t('ui.sign_out')" @click="signOut" />
      </div>
    </div>
  </div>
</template>
<style scoped>
.topbar-account {
  position: relative;
}
.topbar-account-trigger {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  font: inherit;
  cursor: pointer;
}
.topbar-account-trigger:hover {
  background: var(--soft);
  border-color: var(--line);
}
.topbar-account-trigger:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.topbar-account-trigger :deep(svg) {
  width: 14px;
  height: 14px;
  color: var(--muted);
}
.topbar-account-copy {
  display: grid;
  min-width: 82px;
  text-align: start;
}
.topbar-account-copy b,
.topbar-account-identity b {
  font-size: 0.8125rem;
  line-height: 1.2;
}
.topbar-account-copy small,
.topbar-account-identity small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.shell-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--ui-accent);
  color: var(--accent-on);
  font-size: 0.8125rem;
  font-weight: 800;
}
.topbar-account-panel {
  position: absolute;
  z-index: 90;
  inset-inline-end: 0;
  inset-block-start: calc(100% + 8px);
  width: min(320px, calc(100vw - 24px));
  display: grid;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line-strong);
  border-radius: 12px;
  background: var(--surface-overlay, var(--card));
  box-shadow: var(--elev-3);
}
.topbar-account-identity {
  display: flex;
  align-items: center;
  gap: 10px;
}
.topbar-account-identity div {
  display: grid;
}
.topbar-account-actions {
  display: grid;
  gap: 6px;
}
.topbar-account-actions :deep(.ui-button-wrap),
.topbar-account-actions :deep(.ui-button) {
  width: 100%;
}
.topbar-account-actions :deep(.ui-button) {
  justify-content: flex-start;
}
.topbar-account-locale {
  display: grid;
  gap: 6px;
  padding-top: 6px;
  border-top: 1px solid var(--line);
}
.topbar-account-locale p {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--text-2, var(--text));
}
.topbar-account-locale label {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  font-size: 0.875rem;
}
@media (forced-colors: active) {
  .topbar-account-panel {
    border-color: CanvasText;
  }
}
</style>
