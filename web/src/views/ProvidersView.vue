<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { toast } from "../composables/notifications";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";
import {
  addProviderProfileForUi,
  getDefaultProviderProfileId,
  getProviderProfilesForUi,
  getProviderStatusesForUi,
  getProviderWarmupsForUi,
  getWarmOnStartForUi,
  removeProviderProfileForUi,
  saveProviderProfilesForUi,
  setDefaultProviderProfileForUi,
  setWarmOnStartForUi,
  syncResearcherProviderProfiles,
  testProviderProfileForUi,
  warmProviderProfileForUi,
} from "../domain/sharedProviderProfiles";
import ProviderProfileCard from "../components/providers/ProviderProfileCard.vue";
import ProviderSaveBar from "../components/providers/ProviderSaveBar.vue";
import ProviderBulkApply from "../components/providers/ProviderBulkApply.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import type { DiscoveredModel } from "../domain/providerModels";
import { applyProfileFieldValues } from "../domain/providerBulkFields";

type ProviderStatus = { available?: boolean; models?: DiscoveredModel[]; error?: string };
type ProviderWarmup = { message?: string };
const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();

function routeExpandedProfiles() {
  return String(route.query.open || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

const profiles = ref<ProviderProfile[]>([]);
const statuses = ref<Record<string, ProviderStatus>>({});
const warmups = ref<Record<string, ProviderWarmup>>({});
const defaultId = ref("");
const saving = ref(false);
const error = ref("");
const busy = ref<Record<string, string>>({});
const revealedKeys = ref<Record<string, boolean>>({});
const expanded = ref<Record<string, boolean>>(
  Object.fromEntries(routeExpandedProfiles().map((id) => [id, true])),
);
function toggleKeyVisibility(id: string) {
  revealedKeys.value = { ...revealedKeys.value, [id]: !revealedKeys.value[id] };
}
const warmOnStart = ref(false);
function setWarmOnStart(value: boolean) {
  warmOnStart.value = Boolean(setWarmOnStartForUi(value));
}
const snapshot = ref("[]");
const dirty = computed(() => JSON.stringify(profiles.value) !== snapshot.value);

function refreshStatuses() {
  statuses.value = (getProviderStatusesForUi() || {}) as Record<string, ProviderStatus>;
  warmups.value = (getProviderWarmupsForUi() || {}) as Record<string, ProviderWarmup>;
  defaultId.value = String(getDefaultProviderProfileId() || "");
  warmOnStart.value = Boolean(getWarmOnStartForUi());
}
function refresh() {
  profiles.value = (getProviderProfilesForUi() || []) as ProviderProfile[];
  snapshot.value = JSON.stringify(profiles.value);
  refreshStatuses();
}
function discard() {
  refresh();
}
function statusTone(profile: ProviderProfile) {
  const status = statuses.value[profile.id];
  return status?.available ? "ready" : status?.error ? "error" : "idle";
}
function update(profile: ProviderProfile, field: string, value: unknown) {
  (profile as Record<string, unknown>)[field] = value;
}
function endpointPeers(profile: ProviderProfile) {
  const endpoint = String(profile.base_url || "")
    .replace(/\/$/, "")
    .toLocaleLowerCase();
  return profile.type === "ollama"
    ? profiles.value.filter(
        (item) =>
          item.type === "ollama" &&
          String(item.base_url || "")
            .replace(/\/$/, "")
            .toLocaleLowerCase() === endpoint,
      )
    : [];
}
function sharedLimit(profile: ProviderProfile) {
  const peers = endpointPeers(profile);
  return peers.length
    ? Math.min(...peers.map((item) => Math.max(1, Number(item.max_concurrent_requests || 1))))
    : Number(profile.max_concurrent_requests || 1);
}
function statusText(profile: ProviderProfile) {
  const status = statuses.value[profile.id];
  if (status?.available)
    return i18n.tf("providers.ready_models", { count: Number(status.models?.length || 0) });
  return status?.error || warmups.value[profile.id]?.message || i18n.t("providers.not_verified");
}
function copyProfiles() {
  return JSON.parse(JSON.stringify(profiles.value)) as ProviderProfile[];
}
function setBusy(id: string, value = "") {
  busy.value = { ...busy.value, [id]: value };
}
function syncExpandedProfiles() {
  const open = Object.entries(expanded.value)
    .filter(([, value]) => value)
    .map(([id]) => id);
  void router.replace({
    name: "providers",
    query: { ...route.query, open: open.length ? open.join(",") : undefined },
  });
}
function isExpanded(id: string) {
  return expanded.value[id] === true;
}
function toggleExpanded(id: string) {
  expanded.value = { ...expanded.value, [id]: !isExpanded(id) };
  syncExpandedProfiles();
}
async function save() {
  saving.value = true;
  error.value = "";
  try {
    saveProviderProfilesForUi(copyProfiles());
    await syncResearcherProviderProfiles();
    refresh();
    expanded.value = {};
    syncExpandedProfiles();
    toast(i18n.t("providers.saved"), { tone: "success" });
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    saving.value = false;
  }
}
function add(type: "ollama" | "openai") {
  const created = addProviderProfileForUi(type) as ProviderProfile | undefined;
  const edits = profiles.value;
  refresh();
  const known = new Map(edits.map((item) => [item.id, item]));
  profiles.value = profiles.value.map((item) => known.get(item.id) || item);
  const id = created?.id || profiles.value.at(-1)?.id;
  if (id) {
    expanded.value = { ...expanded.value, [id]: true };
    syncExpandedProfiles();
  }
}
function applyBulk(ids: string[], values: Record<string, unknown>) {
  profiles.value = applyProfileFieldValues(profiles.value, ids, values);
  toast(i18n.t("providers.bulk_applied"), { tone: "info" });
}
async function remove(profile: ProviderProfile) {
  if (!window.confirm(i18n.tf("providers.remove_confirm", { name: profile.name || profile.id })))
    return;
  try {
    removeProviderProfileForUi(profile.id);
    profiles.value = profiles.value.filter((item) => item.id !== profile.id);
    if (expanded.value[profile.id]) {
      const next = { ...expanded.value };
      delete next[profile.id];
      expanded.value = next;
      syncExpandedProfiles();
    }
    refreshStatuses();
    snapshot.value = JSON.stringify(profiles.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
function makeDefault(profile: ProviderProfile) {
  setDefaultProviderProfileForUi(profile.id);
  refreshStatuses();
}
async function run(profile: ProviderProfile, action: "test" | "warm") {
  setBusy(profile.id, action);
  error.value = "";
  try {
    if (action === "test") await testProviderProfileForUi(profile.id);
    else await warmProviderProfileForUi(profile.id);
    refreshStatuses();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    setBusy(profile.id);
  }
}
watch(
  () => route.query.open,
  () => {
    const next = Object.fromEntries(routeExpandedProfiles().map((id) => [id, true]));
    if (JSON.stringify(next) !== JSON.stringify(expanded.value)) expanded.value = next;
  },
);

// Provider profiles/statuses are already local synchronous state. Read them during
// setup so the first render contains the actual workspace instead of a one-frame
// loading card that does not correspond to any asynchronous operation.
refresh();
</script>

<template>
  <main class="vue-native-page providers-page" aria-labelledby="providers-page-title">
    <UiPageHeader
      :kicker="i18n.t('section.ai_automation')"
      :title="i18n.t('providers.title')"
      title-id="providers-page-title"
      :description="i18n.t('providers.description')"
      :actions-label="i18n.t('providers.page_actions')"
    >
      <template #actions>
        <button class="btn" type="button" @click="add('ollama')">
          + {{ i18n.t("providers.add_ollama") }}
        </button>
        <button class="btn primary" type="button" @click="add('openai')">
          + {{ i18n.t("providers.add_openai") }}
        </button>
      </template>
    </UiPageHeader>
    <div v-if="error" class="info error" role="alert">{{ error }}</div>
    <p v-if="!profiles.length" class="providers-empty">{{ i18n.t("providers.empty") }}</p>
    <ul v-else class="provider-list" :aria-label="i18n.t('providers.list_label')">
      <ProviderProfileCard
        v-for="profile in profiles"
        :key="profile.id"
        :profile="profile"
        :models="statuses[profile.id]?.models || []"
        :tone="statusTone(profile)"
        :status-text="statusText(profile)"
        :is-default="profile.id === defaultId"
        :expanded="isExpanded(profile.id)"
        :busy="busy[profile.id] || ''"
        :revealed="Boolean(revealedKeys[profile.id])"
        :can-remove="profiles.length > 1"
        :shared-limit="sharedLimit(profile)"
        :shared-endpoint="endpointPeers(profile).length > 1"
        @update="(field, value) => update(profile, field, value)"
        @toggle="toggleExpanded(profile.id)"
        @toggle-key="toggleKeyVisibility(profile.id)"
        @run="(action) => run(profile, action)"
        @make-default="makeDefault(profile)"
        @remove="remove(profile)"
      />
    </ul>
    <details v-if="profiles.length" class="provider-tools">
      <summary>{{ i18n.t("providers.bulk_apply") }}</summary>
      <ProviderBulkApply :profiles="profiles" @apply="applyBulk" />
    </details>
    <label class="provider-warm-option"
      ><input
        type="checkbox"
        :checked="warmOnStart"
        @change="setWarmOnStart(($event.target as HTMLInputElement).checked)"
      /><span
        ><b>{{ i18n.t("providers.warm_on_start") }}</b
        ><small>{{ i18n.t("providers.warm_on_start_help") }}</small></span
      ></label
    >
    <Transition name="providers-save">
      <ProviderSaveBar
        v-if="dirty || saving"
        :saving="saving"
        :can-save="profiles.length > 0"
        @save="save"
        @discard="discard"
      />
    </Transition>
  </main>
</template>

<style scoped>
.providers-page {
  display: grid;
  gap: var(--page-gap);
}
.providers-empty {
  margin: 0;
  padding: 32px;
  border: 1px dashed var(--line);
  border-radius: var(--radius-card);
  color: var(--muted);
  text-align: center;
}
.provider-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.provider-tools {
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-card);
  background: var(--card);
}
.provider-warm-option {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 2px 4px;
  color: var(--muted);
}
.provider-warm-option input {
  inline-size: 18px;
  block-size: 18px;
  margin-top: 2px;
  accent-color: var(--accent);
}
.provider-warm-option span {
  display: grid;
  gap: 2px;
}
.provider-warm-option small {
  font-size: 0.8125rem;
  line-height: 1.45;
}
</style>
