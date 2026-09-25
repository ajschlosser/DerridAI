<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { systemApi, type SystemMetadataExemplar, type SystemMetadataExemplarPage } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";

const i18n = useI18nStore();
const page = ref<SystemMetadataExemplarPage>({
  exists: false, count: 0, limit: 25, offset: 0, rows: [],
  facets: { fields: [], kinds: [], languages: [], scopes: [], schemas: [] },
});
const loading = ref(false);
const error = ref("");
const detail = ref<SystemMetadataExemplar | null>(null);
const filters = ref({ field: "", kind: "", language: "", scope_id: "", schema_id: "", record_id: "" });

const activeFilters = computed(() =>
  Object.entries(filters.value).filter(([, value]) => value.trim()),
);
function t(key: string, fallback: string) { return i18n.t(key, fallback); }
function valueText(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return typeof value === "string" ? value : JSON.stringify(value);
}
async function load(offset = 0) {
  loading.value = true; error.value = "";
  try {
    page.value = await systemApi.systemMetadataExemplars({ ...filters.value, limit: page.value.limit, offset });
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally { loading.value = false; }
}
function filterLabel(key: string) {
  const labels: Record<string, string> = {
    field: t("runtime.system_exemplar_field", "Field"),
    kind: t("runtime.system_exemplar_kind", "Kind"),
    language: t("runtime.system_exemplar_language", "Language"),
    scope_id: t("runtime.system_exemplar_build", "Build"),
    schema_id: t("runtime.system_exemplar_schema", "Schema"),
    record_id: t("runtime.system_exemplar_record", "Record ID"),
  };
  return labels[key] || key;
}
function clearFilter(key: string) {
  (filters.value as Record<string, string>)[key] = "";
  void load(0);
}
function clearAll() {
  filters.value = { field: "", kind: "", language: "", scope_id: "", schema_id: "", record_id: "" };
  void load(0);
}
onMounted(() => void load(0));
</script>

<template>
  <div class="metadata-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("runtime.system_metadata_examples", "Metadata examples") }}</h2>
        <p>{{ t("runtime.system_metadata_exemplars_help", "Evidence-bound examples derived from reviewed corpus metadata. This projection is derived and rebuildable; it is not an ordinary corpus collection.") }}</p>
      </div>
      <strong>{{ page.count.toLocaleString() }}</strong>
    </header>

    <form class="filters" @submit.prevent="load(0)">
      <label><span>{{ t("runtime.system_exemplar_field", "Field") }}</span><select v-model="filters.field" class="control"><option value="">{{ t("runtime.system_all", "All") }}</option><option v-for="item in page.facets.fields" :key="item">{{ item }}</option></select></label>
      <label><span>{{ t("runtime.system_exemplar_kind", "Kind") }}</span><select v-model="filters.kind" class="control"><option value="">{{ t("runtime.system_all", "All") }}</option><option v-for="item in page.facets.kinds" :key="item">{{ item }}</option></select></label>
      <label><span>{{ t("runtime.system_exemplar_language", "Language") }}</span><select v-model="filters.language" class="control"><option value="">{{ t("runtime.system_all", "All") }}</option><option v-for="item in page.facets.languages" :key="item">{{ item }}</option></select></label>
      <label><span>{{ t("runtime.system_exemplar_build", "Build") }}</span><select v-model="filters.scope_id" class="control"><option value="">{{ t("runtime.system_all", "All") }}</option><option v-for="item in page.facets.scopes" :key="item">{{ item }}</option></select></label>
      <label><span>{{ t("runtime.system_exemplar_schema", "Schema") }}</span><select v-model="filters.schema_id" class="control"><option value="">{{ t("runtime.system_all", "All") }}</option><option v-for="item in page.facets.schemas" :key="item">{{ item }}</option></select></label>
      <label><span>{{ t("runtime.system_exemplar_record", "Record ID") }}</span><input v-model="filters.record_id" class="control" type="search" /></label>
      <div class="filter-actions"><button class="btn" type="submit">{{ t("common.apply", "Apply") }}</button><button class="btn" type="button" @click="clearAll">{{ t("runtime.system_clear_all", "Clear all") }}</button></div>
    </form>

    <div v-if="activeFilters.length" class="chips" aria-label="Active filters">
      <button v-for="[key, value] in activeFilters" :key="key" type="button" @click="clearFilter(key)">
        {{ filterLabel(key) }}: {{ value }} <AppIcon name="close" />
      </button>
    </div>

    <div v-if="error" class="state error" role="alert"><strong>{{ t("runtime.system_metadata_failed", "Could not load metadata examples.") }}</strong><span>{{ error }}</span></div>
    <div v-else-if="loading" class="state" role="status">{{ t("runtime.system_metadata_loading", "Loading metadata examples…") }}</div>
    <div v-else-if="!page.exists" class="state">{{ t("runtime.system_metadata_not_built", "The metadata exemplar index has not been built yet.") }}</div>
    <div v-else-if="!page.rows.length" class="state">{{ t("runtime.system_metadata_no_matches", "The index is built, but no examples match these filters.") }}</div>
    <template v-else>
      <div class="example-list">
        <button v-for="item in page.rows" :key="item.exemplar_id" type="button" class="example-row" @click="detail = item">
          <div>
            <strong>{{ item.field_name }} <span aria-hidden="true">→</span> {{ valueText(item.field_value) }}</strong>
            <small>{{ item.record_id }}<template v-if="item.record_revision"> · revision {{ item.record_revision }}</template></small>
          </div>
          <div class="badges"><span>{{ item.kind }}</span><span v-if="item.assertion_status">{{ item.assertion_status }}</span></div>
          <AppIcon name="chevron-right" />
        </button>
      </div>
      <footer class="pagination">
        <span>{{ page.offset + 1 }}–{{ Math.min(page.offset + page.rows.length, page.count) }} of {{ page.count }}</span>
        <div>
          <button class="btn tiny" type="button" :disabled="page.offset <= 0" @click="load(Math.max(0, page.offset - page.limit))">{{ t("common.previous", "Previous") }}</button>
          <button class="btn tiny" type="button" :disabled="page.offset + page.rows.length >= page.count" @click="load(page.offset + page.limit)">{{ t("common.next", "Next") }}</button>
        </div>
      </footer>
    </template>

    <aside v-if="detail" class="detail-panel" aria-label="Metadata example details">
      <header><div><small>{{ t("runtime.system_metadata_example", "Metadata example") }}</small><h3>{{ detail.field_name }} → {{ valueText(detail.field_value) }}</h3></div><button class="icon-btn" type="button"  :aria-label="t('runtime.system_close_details', 'Close details')" @click="detail = null"><AppIcon name="close" /></button></header>
      <dl>
        <div><dt>{{ t("runtime.system_status", "Status") }}</dt><dd>{{ detail.assertion_status || detail.kind }}</dd></div>
        <div><dt>{{ t("runtime.system_source_record", "Source record") }}</dt><dd>{{ detail.record_id }}</dd></div>
        <div><dt>{{ t("runtime.system_source_revision", "Source revision") }}</dt><dd>{{ detail.record_revision ?? "—" }}</dd></div>
        <div><dt>{{ t("runtime.system_build_scope", "Build / scope") }}</dt><dd>{{ detail.scope_id || "—" }}</dd></div>
        <div><dt>{{ t("runtime.system_exemplar_schema", "Schema") }}</dt><dd>{{ detail.schema_id || "—" }} {{ detail.schema_version || "" }}</dd></div>
        <div><dt>{{ t("runtime.system_exemplar_region", "Region") }}</dt><dd>{{ detail.region_type || "—" }}</dd></div>
        <div><dt>{{ t("runtime.system_exemplar_evidence_blocks", "Evidence blocks") }}</dt><dd>{{ (detail.evidence_block_ids || []).join(", ") || "—" }}</dd></div>
        <div><dt>{{ t("runtime.system_exemplar_evidence_hash", "Evidence hash") }}</dt><dd class="mono">{{ detail.evidence_hash || "—" }}</dd></div>
      </dl>
      <section><h4>{{ t("runtime.system_exemplar_context", "Evidence context") }}</h4><p>{{ detail.context_text || "—" }}</p></section>
    </aside>
  </div>
</template>

<style scoped>
.metadata-workspace { display:grid; gap:16px; }
.workspace-heading { display:flex; justify-content:space-between; gap:16px; align-items:start; }
.workspace-heading h2 { margin:0; font-size:1.25rem; }
.workspace-heading p { margin:5px 0 0; max-width:760px; color:var(--muted); line-height:1.5; }
.filters { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; padding:14px; border:1px solid var(--line); border-radius:12px; background:var(--soft); }
.filters label { display:grid; gap:5px; color:var(--muted); font-size:.76rem; font-weight:700; }
.filter-actions { display:flex; align-items:end; gap:6px; }
.chips { display:flex; gap:6px; flex-wrap:wrap; }
.chips button { display:flex; gap:6px; align-items:center; padding:5px 8px; border:1px solid var(--line); border-radius:999px; background:var(--card); color:inherit; font:inherit; font-size:.75rem; cursor:pointer; }
.chips :deep(svg) { width:12px; height:12px; }
.state { display:grid; gap:5px; padding:20px; border:1px solid var(--line); border-radius:12px; background:var(--soft); color:var(--muted); }
.state.error { color:var(--tone-danger-fg); }
.example-list { display:grid; border:1px solid var(--line); border-radius:12px; overflow:hidden; }
.example-row { display:grid; grid-template-columns:minmax(0,1fr) auto 18px; gap:14px; align-items:center; padding:13px 14px; border:0; border-bottom:1px solid var(--line); background:var(--card); color:inherit; text-align:left; cursor:pointer; }
.example-row:last-child { border-bottom:0; }
.example-row:hover { background:var(--soft); }
.example-row strong, .example-row small { display:block; overflow-wrap:anywhere; }
.example-row small { margin-top:4px; color:var(--muted); }
.example-row :deep(svg) { width:16px; height:16px; color:var(--muted); }
.badges { display:flex; gap:5px; flex-wrap:wrap; justify-content:flex-end; }
.badges span { padding:3px 7px; border:1px solid var(--line); border-radius:999px; font-size:.72rem; }
.pagination { display:flex; justify-content:space-between; gap:10px; align-items:center; color:var(--muted); font-size:.8rem; }
.pagination > div { display:flex; gap:6px; }
.detail-panel { position:fixed; z-index:50; top:0; right:0; width:min(520px,100vw); height:100vh; overflow:auto; padding:22px; border-left:1px solid var(--line); background:var(--card); box-shadow:-16px 0 40px color-mix(in srgb,currentColor 10%,transparent); }
.detail-panel header { display:flex; justify-content:space-between; gap:14px; }
.detail-panel h3 { margin:4px 0 0; }
.detail-panel dl { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:22px 0; }
.detail-panel dl div { min-width:0; }
.detail-panel dt { color:var(--muted); font-size:.74rem; font-weight:700; }
.detail-panel dd { margin:3px 0 0; overflow-wrap:anywhere; }
.detail-panel section { border-top:1px solid var(--line); padding-top:16px; }
.detail-panel section h4 { margin:0 0 8px; }
.detail-panel section p { white-space:pre-wrap; line-height:1.55; }
.icon-btn { display:grid; place-items:center; width:34px; height:34px; border:1px solid var(--line); border-radius:8px; background:transparent; color:inherit; cursor:pointer; }
.icon-btn :deep(svg){width:15px;height:15px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
@media(max-width:760px){.filters{grid-template-columns:1fr}.detail-panel dl{grid-template-columns:1fr}.example-row{grid-template-columns:minmax(0,1fr) 18px}.badges{grid-column:1/-1;justify-content:flex-start}.workspace-heading{display:grid}}
</style>
