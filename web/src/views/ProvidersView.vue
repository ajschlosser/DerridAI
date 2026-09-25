<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";
import * as runtime from "../runtime/runtime.js";
import ProviderModelPicker from "../components/ProviderModelPicker.vue";
import ProviderBulkApply from "../components/providers/ProviderBulkApply.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import { MODEL_KINDS, type DiscoveredModel } from "../domain/providerModels";
import { applyProfileFieldValues } from "../domain/providerBulkFields";

type ProviderStatus = { available?: boolean; models?: DiscoveredModel[]; error?: string };
type ProviderWarmup = { message?: string };
const i18n = useI18nStore();
const profiles = ref<ProviderProfile[]>([]);
const statuses = ref<Record<string, ProviderStatus>>({});
const warmups = ref<Record<string, ProviderWarmup>>({});
const defaultId = ref("");
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const busy = ref<Record<string, string>>({});
const revealedKeys = ref<Record<string, boolean>>({});
const expanded = ref<Record<string, boolean>>({});
function toggleKeyVisibility(id: string) {
  revealedKeys.value = { ...revealedKeys.value, [id]: !revealedKeys.value[id] };
}
const warmOnStart = ref(false);
function setWarmOnStart(value: boolean) {
  warmOnStart.value = Boolean(runtime.setWarmOnStartForUi?.(value));
}
const counts = computed(() => ({
  ollama: profiles.value.filter((profile) => profile.type === "ollama").length,
  openai: profiles.value.filter((profile) => profile.type === "openai").length,
}));

function refresh() {
  profiles.value = (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[];
  statuses.value = (runtime.getProviderStatusesForUi?.() || {}) as Record<string, ProviderStatus>;
  warmups.value = (runtime.getProviderWarmupsForUi?.() || {}) as Record<string, ProviderWarmup>;
  defaultId.value = String(runtime.getDefaultProviderProfileId?.() || "");
  warmOnStart.value = Boolean(runtime.getWarmOnStartForUi?.());
}
function update(profile: ProviderProfile, field: string, value: unknown) {
  (profile as Record<string, unknown>)[field] = value;
}
function numeric(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
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
function isExpanded(id: string) {
  return expanded.value[id] !== false;
}
function toggleExpanded(id: string) {
  expanded.value = { ...expanded.value, [id]: !isExpanded(id) };
}
async function save() {
  saving.value = true;
  error.value = "";
  try {
    runtime.saveProviderProfilesForUi?.(copyProfiles());
    await runtime.syncResearcherProviderProfiles?.();
    refresh();
    expanded.value = Object.fromEntries(profiles.value.map((profile) => [profile.id, false]));
    runtime.notifyToast?.(i18n.t("providers.saved"), { tone: "success" });
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    saving.value = false;
  }
}
function add(type: "ollama" | "openai") {
  const created = runtime.addProviderProfileForUi?.(type) as ProviderProfile | undefined;
  refresh();
  const id = created?.id || profiles.value.at(-1)?.id;
  if (id) expanded.value = { ...expanded.value, [id]: true };
}
function applyBulk(ids: string[], values: Record<string, unknown>) {
  profiles.value = applyProfileFieldValues(profiles.value, ids, values);
  runtime.notifyToast?.(i18n.t("providers.bulk_applied"), { tone: "info" });
  for (const id of ids) expanded.value = { ...expanded.value, [id]: true };
}
async function remove(profile: ProviderProfile) {
  if (!window.confirm(i18n.tf("providers.remove_confirm", { name: profile.name || profile.id })))
    return;
  try {
    runtime.removeProviderProfileForUi?.(profile.id);
    refresh();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
function makeDefault(profile: ProviderProfile) {
  runtime.setDefaultProviderProfileForUi?.(profile.id);
  refresh();
}
async function run(profile: ProviderProfile, action: "test" | "warm") {
  setBusy(profile.id, action);
  error.value = "";
  try {
    if (action === "test") await runtime.testProviderProfileForUi?.(profile.id);
    else await runtime.warmProviderProfileForUi?.(profile.id);
    refresh();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    setBusy(profile.id);
  }
}
onMounted(() => {
  refresh();
  loading.value = false;
});
</script>

<template>
  <main class="vue-native-page providers-page" aria-labelledby="providers-page-title">
    <UiPageHeader
      :kicker="i18n.t('section.system')"
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
    <div v-if="error" class="info error" role="alert">{{ error }}</div>
    <section class="providers-overview" aria-labelledby="providers-overview-title">
      <div>
        <p class="eyebrow">{{ i18n.t("providers.registry") }}</p>
        <h2 id="providers-overview-title">{{ i18n.t("providers.registry_title") }}</h2>
        <p>{{ i18n.t("providers.registry_help") }}</p>
      </div>
      <dl class="providers-stats">
        <div>
          <dt>{{ i18n.t("providers.profiles") }}</dt>
          <dd>{{ profiles.length }}</dd>
        </div>
        <div>
          <dt>Ollama</dt>
          <dd>{{ counts.ollama }}</dd>
        </div>
        <div>
          <dt>OpenAI-compatible</dt>
          <dd>{{ counts.openai }}</dd>
        </div>
        <div>
          <dt>{{ i18n.t("providers.default") }}</dt>
          <dd class="default-stat">
            {{ profiles.find((profile) => profile.id === defaultId)?.name || "-" }}
          </dd>
        </div>
      </dl>
    </section>
    <section v-if="loading" class="card" aria-live="polite">{{ i18n.t("ui.loading") }}</section>
    <section v-else class="provider-list" aria-label="Provider profiles">
      <article
        v-for="profile in profiles"
        :key="profile.id"
        class="provider-workspace-card"
        :class="[profile.type, { default: profile.id === defaultId }]"
      >
        <header class="provider-card-header">
          <div class="provider-card-identity">
            <div class="provider-name-row">
              <span class="provider-type">{{
                profile.type === "ollama" ? "OLLAMA" : "OPENAI-COMPATIBLE"
              }}</span
              ><input
                class="control provider-name"
                :aria-label="i18n.t('providers.profile_name')"
                :value="profile.name"
                @input="update(profile, 'name', ($event.target as HTMLInputElement).value)"
              />
            </div>
            <p
              class="provider-status"
              :class="{
                ready: statuses[profile.id]?.available,
                error: !statuses[profile.id]?.available && !!statuses[profile.id]?.error,
              }"
            >
              <span aria-hidden="true"></span>{{ statusText(profile) }}
            </p>
          </div>
          <div class="provider-card-actions">
            <span v-if="profile.id === defaultId" class="status-tag">{{
              i18n.t("providers.default")
            }}</span
            ><button v-else class="btn small" type="button" @click="makeDefault(profile)">
              {{ i18n.t("providers.set_default") }}</button
            ><button
              class="btn small"
              type="button"
              :aria-expanded="isExpanded(profile.id)"
              @click="toggleExpanded(profile.id)"
            >
              {{
                isExpanded(profile.id) ? i18n.t("providers.collapse") : i18n.t("providers.expand")
              }}</button
            ><button
              class="btn small danger"
              type="button"
              :disabled="profiles.length <= 1"
              @click="remove(profile)"
            >
              {{ i18n.t("ui.remove") }}
            </button>
          </div>
        </header>
        <div v-show="isExpanded(profile.id)" class="provider-card-body">
          <div class="provider-field-group">
            <p class="provider-group-title">{{ i18n.t("providers.group_connection") }}</p>
            <div class="provider-fields">
              <label class="field field-wide"
                ><span>{{ i18n.t("providers.endpoint") }}</span
                ><input
                  class="control"
                  :value="profile.base_url"
                  @input="update(profile, 'base_url', ($event.target as HTMLInputElement).value)"
              /></label>
              <ProviderModelPicker
                :profile-name="profile.name || profile.id"
                :model-value="
                  profile.type === 'openai' && profile.model_mode === 'auto'
                    ? 'auto'
                    : String(profile.model || '')
                "
                :models="statuses[profile.id]?.models || []"
                :kind="profile.type === 'openai' ? String(profile.model_kind || 'any') : 'any'"
                :disabled="profile.type === 'openai' && profile.model_mode === 'auto'"
                :busy="busy[profile.id] === 'test'"
                :placeholder="
                  profile.type === 'ollama'
                    ? i18n.t('providers.model_placeholder_ollama')
                    : i18n.t('providers.model_placeholder_openai')
                "
                @update:model-value="update(profile, 'model', $event)"
                @discover="run(profile, 'test')"
              />
              <label v-if="profile.type === 'openai'" class="field"
                ><span>{{ i18n.t("providers.model_mode") }}</span
                ><select
                  class="control"
                  :value="profile.model_mode || 'auto'"
                  @change="
                    update(profile, 'model_mode', ($event.target as HTMLSelectElement).value)
                  "
                >
                  <option value="auto">{{ i18n.t("providers.mode_auto") }}</option>
                  <option value="discovered">{{ i18n.t("providers.mode_discovered") }}</option>
                  <option value="manual">{{ i18n.t("providers.mode_manual") }}</option></select
                ><small>{{ i18n.t("providers.model_mode_help") }}</small></label
              >
              <label v-if="profile.type === 'openai'" class="field"
                ><span>{{ i18n.t("providers.model_kind") }}</span
                ><select
                  class="control"
                  :value="profile.model_kind || 'any'"
                  @change="
                    update(profile, 'model_kind', ($event.target as HTMLSelectElement).value)
                  "
                >
                  <option v-for="kind in MODEL_KINDS" :key="kind" :value="kind">
                    {{ i18n.t(`providers.kind_${kind}`, kind) }}
                  </option></select
                ><small>{{ i18n.t("providers.model_kind_help") }}</small></label
              >
            </div>
          </div>
          <div class="provider-field-group">
            <p class="provider-group-title">{{ i18n.t("providers.group_capacity") }}</p>
            <div class="provider-fields">
              <label class="field"
                ><span>{{ i18n.t("providers.concurrency") }}</span
                ><input
                  class="control"
                  type="number"
                  min="1"
                  max="64"
                  :value="sharedLimit(profile)"
                  @input="
                    update(
                      profile,
                      'max_concurrent_requests',
                      Math.max(
                        1,
                        Math.min(64, numeric(($event.target as HTMLInputElement).value, 1)),
                      ),
                    )
                  "
                /><small>{{
                  profile.type === "ollama" && endpointPeers(profile).length > 1
                    ? i18n.t("providers.shared_endpoint")
                    : i18n.t("providers.concurrency_help")
                }}</small></label
              >
              <label class="field"
                ><span>{{ i18n.t("providers.context") }}</span
                ><input
                  class="control"
                  type="number"
                  min="512"
                  :value="profile.num_ctx || 16384"
                  @input="
                    update(
                      profile,
                      'num_ctx',
                      numeric(($event.target as HTMLInputElement).value, 16384),
                    )
                  "
              /></label>
              <label class="field"
                ><span>{{ i18n.t("providers.max_output") }}</span
                ><input
                  class="control"
                  type="number"
                  min="16"
                  :value="profile.num_predict || 4096"
                  @input="
                    update(
                      profile,
                      'num_predict',
                      numeric(($event.target as HTMLInputElement).value, 4096),
                    )
                  "
              /></label>
            </div>
          </div>
          <div class="provider-field-group">
            <p class="provider-group-title">{{ i18n.t("providers.group_access") }}</p>
            <div class="provider-fields">
              <label v-if="profile.type === 'openai'" class="field"
                ><span>{{ i18n.t("providers.api_key") }}</span
                ><span class="provider-secret-field"
                  ><input
                    class="control"
                    :type="revealedKeys[profile.id] ? 'text' : 'password'"
                    autocomplete="off"
                    :value="profile.api_key"
                    @input="update(profile, 'api_key', ($event.target as HTMLInputElement).value)"
                  /><button
                    type="button"
                    class="btn small provider-secret-toggle"
                    :aria-label="
                      revealedKeys[profile.id]
                        ? i18n.t('providers.hide_api_key')
                        : i18n.t('providers.show_api_key')
                    "
                    @click="toggleKeyVisibility(profile.id)"
                  >
                    {{
                      revealedKeys[profile.id] ? i18n.t("providers.hide") : i18n.t("providers.show")
                    }}
                  </button></span
                ></label
              >
              <label class="provider-access"
                ><input
                  type="checkbox"
                  :checked="Boolean(profile.researcher_enabled)"
                  @change="
                    update(
                      profile,
                      'researcher_enabled',
                      ($event.target as HTMLInputElement).checked,
                    )
                  "
                /><span
                  ><b>{{ i18n.t("providers.researcher_access") }}</b
                  ><small>{{ i18n.t("providers.researcher_access_help") }}</small></span
                ></label
              >
            </div>
          </div>
          <details class="provider-advanced">
            <summary>{{ i18n.t("providers.advanced") }}</summary>
            <div class="provider-field-group">
              <p class="provider-group-title">{{ i18n.t("providers.group_sampling") }}</p>
              <div class="provider-fields advanced-fields">
                <label class="field"
                  ><span>Temperature</span
                  ><input
                    class="control"
                    type="number"
                    min="0"
                    max="2"
                    step="0.01"
                    :value="profile.temperature ?? 0"
                    @input="
                      update(
                        profile,
                        'temperature',
                        numeric(($event.target as HTMLInputElement).value, 0),
                      )
                    "
                /></label>
                <label class="field"
                  ><span>Top P</span
                  ><input
                    class="control"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    :value="profile.top_p ?? 1"
                    @input="
                      update(
                        profile,
                        'top_p',
                        numeric(($event.target as HTMLInputElement).value, 1),
                      )
                    "
                /></label>
                <label v-if="profile.type === 'ollama'" class="field"
                  ><span>Top K</span
                  ><input
                    class="control"
                    type="number"
                    min="0"
                    :value="profile.top_k ?? 0"
                    @input="
                      update(
                        profile,
                        'top_k',
                        numeric(($event.target as HTMLInputElement).value, 0),
                      )
                    "
                /></label>
                <label class="field"
                  ><span>Seed</span
                  ><input
                    class="control"
                    type="number"
                    :value="profile.seed ?? ''"
                    @input="
                      update(profile, 'seed', numeric(($event.target as HTMLInputElement).value, 0))
                    "
                /></label>
              </div>
            </div>
            <div v-if="profile.type === 'ollama'" class="provider-field-group">
              <p class="provider-group-title">{{ i18n.t("providers.group_lifecycle") }}</p>
              <div class="provider-fields advanced-fields">
                <label class="field"
                  ><span>Think</span
                  ><select
                    class="control"
                    :value="String(profile.think ?? 'false')"
                    @change="update(profile, 'think', ($event.target as HTMLSelectElement).value)"
                  >
                    <option value="false">Off</option>
                    <option value="true">On</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select></label
                >
                <label class="field"
                  ><span>Keep alive</span
                  ><input
                    class="control"
                    :value="profile.keep_alive || '10m'"
                    @input="
                      update(profile, 'keep_alive', ($event.target as HTMLInputElement).value)
                    "
                /></label>
              </div>
            </div>
            <div class="provider-field-group">
              <p class="provider-group-title">{{ i18n.t("providers.group_raw") }}</p>
              <div class="provider-fields advanced-fields">
                <label class="field field-wide"
                  ><span>{{ i18n.t("providers.extra_options") }}</span
                  ><textarea
                    class="control provider-json"
                    rows="5"
                    spellcheck="false"
                    :value="String(profile.extra_options || '{}')"
                    @input="
                      update(profile, 'extra_options', ($event.target as HTMLTextAreaElement).value)
                    "
                  ></textarea>
                </label>
              </div>
            </div>
          </details>
          <footer class="provider-card-footer">
            <button
              class="btn small"
              type="button"
              :disabled="Boolean(busy[profile.id])"
              @click="run(profile, 'test')"
            >
              {{
                busy[profile.id] === "test" ? i18n.t("providers.testing") : i18n.t("providers.test")
              }}</button
            ><button
              class="btn small"
              type="button"
              :disabled="Boolean(busy[profile.id])"
              @click="run(profile, 'warm')"
            >
              {{
                busy[profile.id] === "warm" ? i18n.t("providers.warming") : i18n.t("providers.warm")
              }}
            </button>
          </footer>
        </div>
      </article>
    </section>
    <ProviderBulkApply v-if="!loading && profiles.length" :profiles="profiles" @apply="applyBulk" />
    <div class="providers-save">
      <button
        class="btn primary"
        type="button"
        :disabled="saving || !profiles.length"
        @click="save"
      >
        {{ saving ? i18n.t("ui.saving") : i18n.t("ui.save") }}
      </button>
    </div>
  </main>
</template>

<style scoped>
.providers-page {
  display: grid;
  gap: var(--page-gap);
}
.providers-overview {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px 24px;
  padding: 14px 20px;
  border: 1px solid var(--line);
  background: var(--raised);
  box-shadow: var(--shadow-sm);
}
.providers-overview > div:first-child {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}
.providers-overview h2 {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
.providers-overview p:not(.eyebrow) {
  margin: 0;
  color: var(--muted);
  line-height: 1.4;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.eyebrow,
.provider-type {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-fg);
}
.eyebrow {
  flex: none;
  margin: 0;
}
.providers-stats {
  display: flex;
  gap: 18px;
  margin: 0;
  flex: none;
}
.providers-stats div {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}
.providers-stats dt {
  margin: 0;
  font-size: 0.75rem;
  color: var(--muted);
}
.providers-stats dd {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
}
.providers-stats .default-stat {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}
.provider-list {
  display: grid;
  gap: 14px;
}
.provider-card-body {
  display: grid;
  gap: 16px;
}
.provider-workspace-card {
  display: grid;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--line);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  transition:
    box-shadow 0.15s ease,
    border-color 0.15s ease;
}
.provider-workspace-card:hover {
  box-shadow: var(--shadow-md, var(--shadow-sm));
}
.provider-workspace-card.ollama {
  border-left-color: var(--tone-info-border);
}
.provider-workspace-card.openai {
  border-left-color: var(--accent);
}
.provider-workspace-card.default {
  border-color: var(--accent);
  border-left-color: var(--accent);
}
.provider-card-header,
.provider-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
.provider-card-identity {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.provider-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.provider-name {
  min-width: min(320px, 55vw);
  font-size: 1.05rem;
  font-weight: 750;
}
.provider-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 3px 9px 3px 7px;
  width: fit-content;
  border-radius: 999px;
  background: var(--soft);
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 650;
}
.provider-status span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--warning);
  flex: none;
}
.provider-status.ready {
  background: color-mix(in srgb, var(--success) 14%, transparent);
  color: var(--success);
}
.provider-status.ready span {
  background: var(--success);
}
.provider-status.error {
  background: color-mix(in srgb, var(--danger, #c0392b) 14%, transparent);
  color: var(--danger, #c0392b);
}
.provider-status.error span {
  background: var(--danger, #c0392b);
}
.provider-card-actions,
.provider-card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.status-tag {
  padding: 5px 8px;
  background: var(--accent-soft);
  color: var(--accent-fg);
  font-size: 0.75rem;
  font-weight: 800;
}
.provider-field-group {
  display: grid;
  gap: 8px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
.provider-group-title {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.provider-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.field {
  display: grid;
  gap: 6px;
}
.field-wide {
  grid-column: 1/-1;
}
.field > span {
  font-size: 0.75rem;
  font-weight: 700;
}
.field small,
.provider-access small {
  color: var(--muted);
  line-height: 1.4;
}
.provider-access {
  grid-column: 1/-1;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid var(--line);
  background: var(--soft);
}
.provider-access input {
  margin-top: 3px;
  accent-color: var(--accent);
}
.provider-access span {
  display: grid;
  gap: 3px;
}
.provider-secret-field {
  display: flex;
  gap: 6px;
  align-items: center;
}
.provider-secret-field .control {
  flex: 1;
  min-width: 0;
}
.provider-secret-toggle {
  flex: 0 0 auto;
  white-space: nowrap;
}
.provider-json {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  font-size: 0.8rem;
}
.providers-save {
  position: sticky;
  bottom: 0;
  z-index: 4;
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
  padding: 14px 0;
  border-top: 1px solid var(--line);
  background: color-mix(in srgb, var(--panel) 97%, transparent);
  backdrop-filter: blur(8px);
}
@media (max-width: 800px) {
  .providers-overview {
    flex-direction: column;
    align-items: stretch;
  }
  .providers-overview > div:first-child {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  .providers-stats {
    flex-wrap: wrap;
  }
  .provider-card-header {
    flex-direction: column;
  }
  .provider-fields {
    grid-template-columns: 1fr;
  }
  .field-wide,
  .provider-access {
    grid-column: auto;
  }
  .provider-name {
    min-width: 0;
    width: 100%;
  }
}
.provider-advanced {
  border-top: 1px solid var(--line);
  padding-top: 14px;
}
.provider-advanced summary {
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 750;
  color: var(--accent-fg);
}
.provider-advanced .provider-field-group:first-of-type {
  border-top: none;
  padding-top: 14px;
}
.provider-warm-option {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.provider-warm-option input {
  inline-size: 18px;
  block-size: 18px;
  margin-top: 2px;
}
.provider-warm-option span {
  display: grid;
  gap: 2px;
}
.provider-warm-option small {
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
</style>
