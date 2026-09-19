<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import UiButton from "../ui/UiButton.vue";
import UiField from "../ui/UiField.vue";
import { useI18nStore } from "../../stores/i18n";
import { parseChromaHttpUrl } from "../../domain/chromaConnection";
import type { ChromaConnectionUpdate, ChromaHealth, ChromaMode } from "../../types/vector";

const props = defineProps<{
  health: ChromaHealth | null;
  probing?: boolean;
  applying?: boolean;
  probeResult?: ChromaHealth | null;
  error?: string;
}>();
const emit = defineEmits<{
  probe: [body: ChromaConnectionUpdate];
  apply: [body: ChromaConnectionUpdate];
}>();
const i18n = useI18nStore();
const mode = ref<ChromaMode>(props.health?.mode || "embedded");
const path = ref(props.health?.path || props.health?.host_path_hint || "/data/chroma");
const url = ref(props.health?.url || "http://chroma:8000");
const token = ref("");
const tenant = ref(props.health?.tenant || "default_tenant");
const database = ref(props.health?.database || "default_database");
const urlError = ref("");
const pathError = ref("");
const modeGroup = useId();

watch(() => props.health, value => {
  if (!value) return;
  mode.value = value.mode;
  if (value.path || value.host_path_hint) path.value = value.path || value.host_path_hint || path.value;
  if (value.url) url.value = value.url;
  if (value.tenant) tenant.value = value.tenant;
  if (value.database) database.value = value.database;
});

const body = computed<ChromaConnectionUpdate>(() => {
  if (mode.value === "embedded") return {mode: "embedded", path: path.value.trim()};
  return {
    mode: "http",
    url: url.value.trim(),
    token: token.value.trim() ? token.value.trim() : null,
    tenant: tenant.value.trim() || "default_tenant",
    database: database.value.trim() || "default_database",
  };
});

function validate(): boolean {
  urlError.value = "";
  pathError.value = "";
  if (mode.value !== "http") {
    if (path.value.trim()) return true;
    pathError.value = i18n.t("vector.enter_storage_path", "Enter a Chroma storage path");
    return false;
  }
  try {
    parseChromaHttpUrl(url.value);
    return true;
  } catch (error) {
    urlError.value = error instanceof Error && error.message === "url-credentials"
      ? i18n.t("vector.chroma_url_credentials", "Do not put credentials in the URL. Use the access token field.")
      : i18n.t("vector.chroma_url_help", "Enter an absolute http(s) Chroma URL.");
    return false;
  }
}
function probe() { if (validate()) emit("probe", body.value); }
function apply() { if (validate()) emit("apply", body.value); }
</script>
<template>
  <form class="vector-backend-panel" @submit.prevent="apply">
    <p>{{ i18n.t("vector.connection_help", "Choose local persistent storage, the Chroma container DerridAI provides, or a server you already run. Switching backends does not migrate collections.") }}</p>
    <fieldset class="vector-mode-choice">
      <legend>{{ i18n.t("vector.connection_mode", "Storage backend") }}</legend>
      <label :class="{selected: mode==='embedded'}">
        <input type="radio" :name="modeGroup" value="embedded" v-model="mode">
        <span><b>{{ i18n.t("vector.connection_mode_embedded", "Local filesystem") }}</b><small>{{ i18n.t("vector.connection_mode_embedded_help", "Embedded Chroma on the host-mounted data directory.") }}</small></span>
      </label>
      <label :class="{selected: mode==='http'}">
        <input type="radio" :name="modeGroup" value="http" v-model="mode">
        <span><b>{{ i18n.t("vector.connection_mode_http", "Running Chroma server") }}</b><small>{{ i18n.t("vector.connection_mode_http_help", "Connect over HTTP to the compose chroma service or a host-run server.") }}</small></span>
      </label>
    </fieldset>
    <template v-if="mode==='embedded'">
    <UiField :label="i18n.t('vector.container_path', 'Container path')" :hint="i18n.t('vector.container_path_help', 'Path inside the DerridAI API container, inside the mounted data root.')">
      <input id="chroma-path" class="control" v-model="path" spellcheck="false" autocomplete="off" :aria-invalid="pathError ? 'true' : undefined">
    </UiField>
    <p v-if="pathError" class="vector-field-error" role="alert">{{ pathError }}</p>
    </template>
    <template v-else>
      <UiField :label="i18n.t('vector.chroma_url', 'Chroma server URL')" :hint="i18n.t('vector.chroma_url_help', 'Absolute http(s) origin, for example http://chroma:8000.')">
        <input id="chroma-url" class="control" v-model="url" spellcheck="false" inputmode="url" autocomplete="off" :aria-invalid="urlError ? 'true' : undefined">
      </UiField>
      <p v-if="urlError" class="vector-field-error" role="alert">{{ urlError }}</p>
      <p class="note">{{ i18n.t("vector.compose_profile_help", "Start the bundled service with docker compose --profile chroma up -d, then use http://chroma:8000 from the API container.") }}</p>
      <UiField :label="i18n.t('vector.chroma_token', 'Access token')" :hint="health?.token_configured ? i18n.t('vector.chroma_token_kept', 'A token is already configured. Leave this field blank to keep it.') : i18n.t('vector.chroma_token_help', 'Optional Bearer token.')">
        <input id="chroma-token" class="control" v-model="token" type="password" autocomplete="off">
      </UiField>
      <div class="vector-tenant-grid">
        <UiField :label="i18n.t('vector.chroma_tenant', 'Tenant')" :hint="i18n.t('vector.chroma_tenant_help', 'Leave the default unless this server is shared.')">
          <input class="control" v-model="tenant" autocomplete="off">
        </UiField>
        <UiField :label="i18n.t('vector.chroma_database', 'Database')" :hint="i18n.t('vector.chroma_database_help', 'Leave the default unless this server is shared.')">
          <input class="control" v-model="database" autocomplete="off">
        </UiField>
      </div>
    </template>
    <div class="info warn" role="note">
      <b>{{ i18n.t("vector.connection_switch_caution", "Changing backend does not move existing collections.") }}</b>
      <span>{{ i18n.t("vector.connection_switch_caution_help", "DerridAI will use the selected backend immediately. Collections stay where they are until you rebuild or restore them.") }}</span>
    </div>
    <div v-if="probeResult" class="info" :class="{warn: !probeResult.available}" role="status">
      <b>{{ probeResult.available ? i18n.t("vector.connection_ok", "Chroma is reachable") : i18n.t("vector.health_unavailable", "Chroma unavailable") }}</b>
      <span>{{ probeResult.identity }}{{ probeResult.error ? ` · ${probeResult.error}` : "" }}</span>
    </div>
    <p v-if="error" class="vector-field-error" role="alert">{{ error }}</p>
    <div class="vector-backend-actions">
      <UiButton type="button" :label="probing ? i18n.t('vector.connection_probing', 'Testing connection…') : i18n.t('vector.connection_probe', 'Test connection')" :disabled="probing || applying" @click="probe" />
      <UiButton type="submit" variant="primary" :label="i18n.t('vector.connection_apply', 'Apply connection')" :disabled="probing || applying" />
    </div>
  </form>
</template>
<style scoped>
.vector-backend-panel{display:grid;gap:14px}
.vector-backend-panel>p,.vector-backend-panel .note{margin:0;color:var(--muted);font-size:.8125rem;line-height:1.5}
.vector-mode-choice{display:grid;gap:8px;margin:0;padding:0;border:0}
.vector-mode-choice legend{margin-bottom:6px;font-size:.8125rem;font-weight:750}
.vector-mode-choice label{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px;align-items:start;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--panel);cursor:pointer}
.vector-mode-choice label.selected{border-color:var(--accent);background:var(--accent-soft)}
.vector-mode-choice small{display:block;margin-top:4px;color:var(--muted);font-size:.8125rem;line-height:1.45;font-weight:500}
.vector-tenant-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.vector-backend-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.vector-field-error{margin:0;color:var(--danger);font-size:.8125rem}
.vector-backend-panel :deep(.control){min-height:40px;font-size:.8125rem}
.vector-mode-choice input{width:16px;height:16px;margin-top:3px}
@media(max-width:700px){.vector-tenant-grid{grid-template-columns:1fr}}
</style>
