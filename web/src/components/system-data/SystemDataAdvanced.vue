<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { systemApi, type SystemChromaCollection, type SystemChromaCommandResult } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";

const i18n = useI18nStore();
const collections = ref<SystemChromaCollection[]>([]);
const loading = ref(false);
const error = ref("");
const command = ref("");
const validation = ref<SystemChromaCommandResult | null>(null);
const result = ref<SystemChromaCommandResult | null>(null);
const busy = ref(false);

function t(key: string, fallback: string) { return i18n.t(key, fallback); }

async function load() {
  loading.value = true; error.value = "";
  try {
    collections.value = (await systemApi.systemChromaCollections()).collections || [];
    if (!command.value && collections.value[0]) command.value = `get ${collections.value[0].name} --limit 10`;
  } catch (cause) {
    collections.value = [];
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally { loading.value = false; }
}
function choose(name: string) {
  command.value = `get ${name} --limit 10`;
  validation.value = null;
  result.value = null;
}
async function validate() {
  busy.value = true; error.value = ""; result.value = null;
  try { validation.value = await systemApi.validateSystemChroma(command.value); }
  catch (cause) { validation.value = null; error.value = cause instanceof Error ? cause.message : String(cause); }
  finally { busy.value = false; }
}
async function execute() {
  busy.value = true; error.value = "";
  try {
    validation.value = await systemApi.validateSystemChroma(command.value);
    result.value = await systemApi.querySystemChroma(command.value);
  } catch (cause) {
    result.value = null;
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally { busy.value = false; }
}
onMounted(() => void load());
</script>

<template>
  <div class="advanced-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("runtime.system_advanced", "Advanced") }}</h2>
        <p>{{ t("runtime.system_chroma_help", "Inspect DerridAI-owned internal vector collections with a restricted, read-only command console. Corpus collections and mutation commands are not available here.") }}</p>
      </div>
      <button class="btn" type="button" :disabled="loading" @click="load"><AppIcon name="refresh" /> {{ t("common.refresh", "Refresh") }}</button>
    </header>

    <div v-if="loading" class="state" role="status">{{ t("runtime.system_checking_vectors", "Checking internal vector collections…") }}</div>
    <div v-else-if="error && !collections.length" class="state error" role="alert">
      <strong>{{ t("runtime.system_vector_unavailable", "Internal vector storage is unavailable.") }}</strong>
      <span>{{ error }}</span>
    </div>
    <div v-else-if="!collections.length" class="state">{{ t("runtime.system_no_internal_vectors", "No internal vector collections are available.") }}</div>
    <template v-else>
      <section class="collections" aria-labelledby="collections-title">
        <div class="section-heading"><div><h3 id="collections-title">{{ t("runtime.system_internal_vectors", "Internal vector collections") }}</h3><p>{{ t("runtime.system_internal_vectors_roles", "Select a collection to prepare a valid read-only command.") }}</p></div><strong>{{ collections.length }}</strong></div>
        <div class="collection-grid">
          <button v-for="item in collections" :key="item.name" type="button" @click="choose(item.name)">
            <div><strong>{{ item.name }}</strong><small>{{ item.role || "system" }}<template v-if="item.derived"> · derived</template></small></div>
            <span>{{ item.count.toLocaleString() }}</span>
          </button>
        </div>
      </section>

      <section class="console" aria-labelledby="console-title">
        <div class="section-heading">
          <div><h3 id="console-title">{{ t("runtime.system_chroma_console", "Read-only query console") }}</h3><p>{{ t("runtime.system_chroma_examples", "Examples: get collection_name --limit 10 · query collection_name --text "responsibility" --n-results 8") }}</p></div>
          <span class="readonly"><AppIcon name="lock" /> {{ t("runtime.system_read_only", "Read only") }}</span>
        </div>
        <label class="command-field"><span>{{ t("runtime.system_chroma_command", "Command") }}</span><textarea v-model="command" rows="4" spellcheck="false" /></label>
        <div class="console-actions">
          <button class="btn" type="button" :disabled="busy || !command.trim()" @click="validate">{{ t("runtime.system_validate_command", "Validate & explain") }}</button>
          <button class="btn primary" type="button" :disabled="busy || !command.trim()" @click="execute">{{ t("runtime.system_run_command", "Run read-only query") }}</button>
        </div>
        <div v-if="error" class="state error" role="alert">{{ error }}</div>
        <div v-if="validation" class="explanation">
          <AppIcon name="check" />
          <div><strong>{{ t("runtime.system_command_valid", "Valid read-only command") }}</strong><p>{{ validation.explanation }}</p><small v-if="validation.embedding_provider">{{ t("runtime.system_embedding", "Embedding") }}: {{ validation.embedding_provider }}<template v-if="validation.embedding_model"> / {{ validation.embedding_model }}</template></small></div>
        </div>
        <details v-if="result?.result" class="result">
          <summary>{{ t("runtime.system_query_results", "Query results") }}</summary>
          <pre>{{ JSON.stringify(result.result, null, 2) }}</pre>
        </details>
      </section>
    </template>
  </div>
</template>

<style scoped>
.advanced-workspace{display:grid;gap:18px}.workspace-heading,.section-heading{display:flex;justify-content:space-between;gap:16px;align-items:start}.workspace-heading h2,.section-heading h3{margin:0}.workspace-heading h2{font-size:1.25rem}.workspace-heading p,.section-heading p{margin:5px 0 0;max-width:760px;color:var(--muted);line-height:1.5}.workspace-heading :deep(svg){width:16px;height:16px}.state{display:grid;gap:5px;padding:20px;border:1px solid var(--line);border-radius:12px;background:var(--soft);color:var(--muted)}.state.error{color:var(--tone-danger-fg)}.collections,.console{display:grid;gap:12px;padding:16px;border:1px solid var(--line);border-radius:13px;background:var(--card)}.collection-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.collection-grid button{display:flex;justify-content:space-between;gap:12px;padding:11px;border:1px solid var(--line);border-radius:9px;background:var(--soft);color:inherit;text-align:left;cursor:pointer}.collection-grid strong,.collection-grid small{display:block}.collection-grid small{margin-top:3px;color:var(--muted)}.collection-grid>button>span{font-weight:750}.readonly{display:flex;gap:5px;align-items:center;padding:4px 7px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:.75rem}.readonly :deep(svg){width:13px;height:13px}.command-field{display:grid;gap:6px;color:var(--muted);font-size:.77rem;font-weight:700}.command-field textarea{width:100%;resize:vertical;padding:10px;border:1px solid var(--line);border-radius:9px;background:var(--soft);color:inherit;font:500 .82rem/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}.console-actions{display:flex;gap:7px;flex-wrap:wrap}.explanation{display:flex;gap:10px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.explanation>:deep(svg){flex:0 0 auto;width:17px;height:17px}.explanation p{margin:4px 0;color:var(--muted);line-height:1.5}.explanation small{color:var(--muted)}.result summary{cursor:pointer;font-weight:700}.result pre{max-height:420px;overflow:auto;padding:12px;border:1px solid var(--line);border-radius:9px;background:var(--soft);font-size:.76rem;white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:720px){.workspace-heading,.section-heading{display:grid}.collection-grid{grid-template-columns:1fr}}
</style>
