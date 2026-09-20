<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import UiButton from "./ui/UiButton.vue";
import UiDialog from "./ui/UiDialog.vue";
import { useI18nStore } from "../stores/i18n";
import * as runtime from "../runtime/runtime.js";

type TouchupItem = { file: { name?: string; records: Record<string, any>[] }; index: number; record: Record<string, any>; key: string };
type TouchupResult = { item: TouchupItem; proposal: any; error?: unknown };
type WorkspaceInfo = { items: TouchupItem[]; initialMode: string; availableFields: string[]; attributionPreset: string[]; semanticPreset: string[]; defaultSelection: string[]; groups: { name: string; fields: string[] }[]; highRiskFields: string[]; fieldLabels: Record<string, string>; profiles: any[]; providerProfileId: string; defaultMode: string };

const i18n = useI18nStore();
const open = ref(false);
const info = ref<WorkspaceInfo | null>(null);
const mode = ref<"foreground" | "background" | "auto">("foreground");
const profileId = ref("");
const model = ref("");
const instructions = ref("");
const selection = ref<string[]>([]);
const status = ref<any>(null);
const running = ref(false);
const stopped = ref(false);
const results = ref<Record<string, TouchupResult>>({});
const approvals = ref<Record<string, string[]>>({});
const expanded = ref<string[]>([]);
const activeIndex = ref(-1);
const error = ref("");

const items = computed(() => info.value?.items || []);
const profile = computed(() => info.value?.profiles.find(item => item.id === profileId.value));
const selectedCount = computed(() => selection.value.length);
const proposedCount = computed(() => Object.values(results.value).reduce((count, result) => count + Object.keys(result.proposal?.changes || {}).length, 0));
const approvedCount = computed(() => Object.values(approvals.value).reduce((count, fields) => count + fields.length, 0));
const title = computed(() => mode.value === "auto" ? i18n.t("operations.job.auto", "Auto-improve") : i18n.t("llm.review_workspace", "LLM Review Workspace"));
const canRun = computed(() => selectedCount.value > 0 && Boolean(model.value.trim() || profile.value?.model || status.value?.configured_model));
const statusLabel = computed(() => {
  if (!status.value) return i18n.t("llm.checking_provider", "Checking provider…");
  return status.value.available ? i18n.t("llm.provider_ready", "Provider ready") : i18n.t("llm.provider_unavailable", "Provider unavailable");
});

function reset(next: { items: TouchupItem[]; initialMode: string }) {
  info.value = runtime.touchupWorkspaceInfo(next.items, next.initialMode) as WorkspaceInfo;
  mode.value = next.initialMode === "auto" ? "auto" : (info.value.defaultMode as typeof mode.value);
  profileId.value = info.value.providerProfileId;
  selection.value = [...info.value.defaultSelection];
  model.value = String(info.value.profiles.find(item => item.id === profileId.value)?.model || "");
  instructions.value = "";
  status.value = null;
  running.value = false;
  stopped.value = false;
  results.value = {};
  approvals.value = {};
  expanded.value = items.value[0]?.key ? [items.value[0].key] : [];
  activeIndex.value = -1;
  error.value = "";
  open.value = true;
  void refreshStatus();
}
function onOpen(event: Event) {
  const detail = (event as CustomEvent<{ items: TouchupItem[]; initialMode: string }>).detail;
  if (detail?.items?.length) reset(detail);
}
function close() { stopped.value = true; open.value = false; }
async function refreshStatus() {
  if (!profileId.value) return;
  status.value = await runtime.touchupProviderStatus(profileId.value);
  if (!model.value) model.value = String(status.value?.configured_model || profile.value?.model || "");
}
function setMode(value: string) { mode.value = value as typeof mode.value; if (mode.value !== "auto") runtime.state.appConfig.default_llm_run_mode = mode.value; runtime.persistPrefs(); }
function setProfile(value: string) { profileId.value = value; model.value = String(info.value?.profiles.find(item => item.id === value)?.model || ""); status.value = null; void refreshStatus(); }
function toggleField(field: string, checked: boolean) {
  if (checked && field === "text") selection.value = ["text"];
  else if (checked) selection.value = [...selection.value.filter(item => item !== "text" && item !== field), field];
  else selection.value = selection.value.filter(item => item !== field);
}
function choosePreset(preset: string) {
  selection.value = preset === "text" ? (info.value?.availableFields.includes("text") ? ["text"] : []) : [...(preset === "semantic" ? info.value?.semanticPreset || [] : info.value?.attributionPreset || [])];
}
function isExpanded(key: string) { return expanded.value.includes(key); }
function toggleExpanded(key: string) { expanded.value = isExpanded(key) ? expanded.value.filter(item => item !== key) : [...expanded.value, key]; }
function pretty(value: unknown) { if (typeof value === "string") return value; try { return JSON.stringify(value, null, 2); } catch { return String(value); } }
function fieldsFor(result: TouchupResult) { return Object.keys(result.proposal?.changes || {}); }
function checked(item: TouchupItem, field: string) { return (approvals.value[item.key] || []).includes(field); }
function setChecked(item: TouchupItem, field: string, value: boolean) {
  const fields = new Set(approvals.value[item.key] || []);
  value ? fields.add(field) : fields.delete(field);
  approvals.value[item.key] = [...fields];
}
async function run() {
  if (running.value || !canRun.value) return;
  if (selection.value.includes("text") && selection.value.length > 1) { error.value = i18n.t("llm.text_review_separate", "Text review must run separately from metadata."); return; }
  const config = runtime.touchupRequestConfig(profileId.value, model.value.trim(), selection.value);
  if (!config?.model) { error.value = i18n.t("llm.model_required", "No model selected."); return; }
  error.value = "";
  if (mode.value !== "foreground") {
    running.value = true;
    try { await runtime.touchupSubmitBackground(items.value, config, selection.value, instructions.value, mode.value); close(); }
    catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); running.value = false; }
    return;
  }
  results.value = {};
  approvals.value = {};
  running.value = true;
  stopped.value = false;
  for (let index = 0; index < items.value.length; index += 1) {
    if (stopped.value) break;
    activeIndex.value = index;
    const item = items.value[index];
    try {
      const proposal = await runtime.touchupRequest(item, selection.value, config, instructions.value);
      results.value[item.key] = { item, proposal };
      approvals.value[item.key] = Object.keys(proposal.changes || {}).filter(field => field !== "text");
    } catch (exc) {
      results.value[item.key] = { item, proposal: null, error: exc };
      approvals.value[item.key] = [];
    }
    expanded.value = [...new Set([...expanded.value, item.key])];
  }
  activeIndex.value = -1;
  running.value = false;
}
function reviewAgain() { results.value = {}; approvals.value = {}; stopped.value = false; error.value = ""; }
function selectAllChanges() { for (const result of Object.values(results.value)) if (result.proposal) approvals.value[result.item.key] = fieldsFor(result); }
function clearChanges() { for (const result of Object.values(results.value)) approvals.value[result.item.key] = []; }
function apply(all = false, reviewOnly = false) {
  runtime.touchupApplyResults(items.value, results.value, approvals.value, all, reviewOnly);
  close();
}
onMounted(() => window.addEventListener("derridai:open-touchup", onOpen));
onBeforeUnmount(() => window.removeEventListener("derridai:open-touchup", onOpen));
watch(profileId, () => { if (open.value && !status.value) void refreshStatus(); });
</script>

<template>
  <UiDialog v-if="info" :open="open" size="xlarge" :title="title" :description="i18n.tf('llm.review_workspace_summary','{count} record(s) · review proposals before applying changes.',{count:items.length})" :close-label="i18n.t('ui.close','Close')" @close="close">
    <div class="workspace-grid">
      <aside class="workspace-config">
        <section class="workspace-section">
          <h3>{{ i18n.t("llm.run_mode", "Run mode") }}</h3>
          <select class="control" :value="mode" @change="setMode(($event.target as HTMLSelectElement).value)">
            <option value="foreground">{{ i18n.t("llm.interactive_foreground", "Interactive foreground") }}</option>
            <option value="background">{{ i18n.t("llm.background_review", "Background review") }}</option>
            <option value="auto">{{ i18n.t("operations.job.auto", "Background Auto-improve") }}</option>
          </select>
        </section>
        <section class="workspace-section">
          <h3>{{ i18n.t("llm.provider_profile", "Provider profile") }}</h3>
          <select class="control" :value="profileId" @change="setProfile(($event.target as HTMLSelectElement).value)">
            <option v-for="item in info.profiles" :key="item.id" :value="item.id">{{ item.name || item.id }}</option>
          </select>
          <p class="workspace-status" :data-state="status?.available ? 'ready' : status ? 'error' : 'pending'">{{ statusLabel }}</p>
        </section>
        <section class="workspace-section">
          <h3>{{ i18n.t("llm.review_preset", "Review preset") }}</h3>
          <div class="preset-row"><UiButton size="small" :label="i18n.t('llm.attribution','Attribution')" @click="choosePreset('attribution')"/><UiButton size="small" :label="i18n.t('llm.semantics','Semantics')" @click="choosePreset('semantic')"/><UiButton size="small" :label="i18n.t('llm.ocr_text','OCR / text')" @click="choosePreset('text')"/></div>
        </section>
        <section class="workspace-section">
          <h3>{{ i18n.t("llm.allowed_fields", "Allowed fields") }}</h3>
          <div class="field-actions"><UiButton size="small" :label="i18n.t('llm.select_metadata','Select metadata')" @click="selection = info.availableFields.filter(field => field !== 'text').slice(0, 12)"/><UiButton size="small" :label="i18n.t('ui.clear','Clear')" @click="selection = []"/><span>{{ selectedCount }}</span></div>
          <div v-for="group in info.groups" :key="group.name" class="field-group" v-show="group.fields.some(field => info.availableFields.includes(field))"><h4>{{ group.name }}</h4><label v-for="field in group.fields" v-show="info.availableFields.includes(field)" :key="field" class="check-item"><input type="checkbox" :checked="selection.includes(field)" @change="toggleField(field, ($event.target as HTMLInputElement).checked)"><span>{{ info.fieldLabels[field] || field }}</span><small v-if="info.highRiskFields.includes(field)">{{ i18n.t('llm.verify','verify') }}</small></label></div>
        </section>
        <section class="workspace-section"><h3>{{ i18n.t("llm.model", "Model") }}</h3><input v-model="model" class="control" :placeholder="i18n.t('llm.model_name','Model name')"><label class="instruction-field"><span>{{ i18n.t("llm.additional_instructions", "Additional instructions") }}</span><textarea v-model="instructions" :placeholder="i18n.t('llm.instructions_optional','Optional instructions applied to every record in this batch.')"></textarea></label></section>
      </aside>
      <section class="workspace-results" aria-live="polite">
        <div v-if="running && mode === 'auto'" class="auto-improve-running"><div class="spinner"></div><h3>{{ i18n.t('llm.auto_progress','Auto-improve pass in progress') }}</h3><p>{{ Object.keys(results).length }} / {{ items.length }} {{ i18n.t('llm.records_reviewed','records reviewed') }}</p><div class="batch-progress-bar"><i :style="{width: `${Math.round(Object.keys(results).length / Math.max(items.length, 1) * 100)}%`}"/></div></div>
        <template v-else>
          <header class="queue-header"><div><b>{{ running ? i18n.t('llm.review_in_progress','Review in progress') : mode === 'auto' ? i18n.t('llm.auto_results','Auto-improve results') : i18n.t('llm.review_queue','Review queue') }}</b><span>{{ Object.keys(results).length }} / {{ items.length }} · {{ proposedCount }} {{ i18n.t('llm.proposed_changes','proposed changes') }}</span></div><div class="queue-tools"><UiButton size="small" :label="i18n.t('llm.expand_all','Expand all')" @click="expanded = items.map(item => item.key)"/><UiButton size="small" :label="i18n.t('llm.collapse_all','Collapse all')" @click="expanded = []"/><UiButton v-if="proposedCount" size="small" :label="i18n.t('llm.select_all_changes','Select all changes')" @click="selectAllChanges"/><UiButton v-if="proposedCount" size="small" :label="i18n.t('llm.select_none','Select none')" @click="clearChanges"/></div></header>
          <section v-for="(item, index) in items" :key="item.key" class="queue-card" :class="{active: running && activeIndex === index, error: results[item.key]?.error}">
            <button type="button" class="queue-summary" @click="toggleExpanded(item.key)"><span class="queue-index">{{ index + 1 }}</span><span><b>{{ item.record.record_id || `Record ${index + 1}` }}</b><small>{{ item.record.work || item.file.name }} · {{ item.record.page_start || '?' }}</small></span><span class="queue-status">{{ results[item.key]?.error ? i18n.t('llm.failed','Failed') : results[item.key] ? `${Object.keys(results[item.key].proposal?.changes || {}).length} ${i18n.t('llm.changes','changes')}` : running && activeIndex === index ? i18n.t('llm.reviewing','Reviewing') : i18n.t('llm.queued','Queued') }}</span><span aria-hidden="true">{{ isExpanded(item.key) ? '▾' : '▸' }}</span></button>
            <div v-if="isExpanded(item.key)" class="queue-body">
              <div v-if="!results[item.key]" class="empty-result">{{ running && activeIndex === index ? i18n.t('llm.waiting_model','Waiting for model…') : i18n.t('llm.waiting_queue','Waiting in queue.') }}</div>
              <div v-else-if="results[item.key].error" class="llm-error" role="alert">{{ results[item.key].error instanceof Error ? results[item.key].error.message : String(results[item.key].error) }}</div>
              <template v-else><div class="record-actions"><UiButton size="small" :label="i18n.t('llm.select_record_changes','Select record changes')" @click="approvals[item.key] = fieldsFor(results[item.key])"/><UiButton size="small" :label="i18n.t('llm.clear_record','Clear record')" @click="approvals[item.key] = []"/></div><article v-for="field in fieldsFor(results[item.key])" :key="field" class="proposal"><header><label><input type="checkbox" :checked="checked(item, field)" @change="setChecked(item, field, ($event.target as HTMLInputElement).checked)"> {{ info.fieldLabels[field] || field }}</label><small v-if="info.highRiskFields.includes(field)">{{ i18n.t('llm.verify','verify carefully') }}</small></header><div class="proposal-grid"><div><b>{{ i18n.t('llm.current','Current') }}</b><pre>{{ pretty(item.record[field]) }}</pre></div><div><b>{{ i18n.t('llm.proposed','Proposed') }}</b><pre>{{ pretty(results[item.key].proposal.changes[field]) }}</pre></div></div><p>{{ results[item.key].proposal.rationale?.[field] || i18n.t('llm.no_rationale','No rationale supplied.') }}</p></article></template>
            </div>
          </section>
        </template>
      </section>
    </div>
    <template #footer><span class="footer-note">{{ error || (running ? i18n.t('llm.review_running','Review is running. Completed records remain inspectable.') : `${approvedCount} ${i18n.t('llm.selected_changes','selected changes')}`) }}</span><div class="footer-actions"><UiButton :label="i18n.t('ui.close','Close')" @click="close"/><UiButton v-if="!running && Object.keys(results).length" :label="i18n.t('llm.review_again','Review again')" @click="reviewAgain"/><UiButton v-if="!running && proposedCount" variant="soft" :label="i18n.t('llm.accept_all','Accept all changes')" @click="apply(true)"/><UiButton v-if="!running && Object.keys(results).length" variant="primary" :disabled="!canRun" :label="i18n.t('llm.apply_selected','Apply selected')" @click="apply(false)"/><UiButton v-if="!running && !Object.keys(results).length" variant="primary" :disabled="!canRun" :label="mode === 'auto' ? i18n.t('operations.job.auto','Auto-improve') : i18n.t('llm.run_review','Run review')" @click="run"/></div></template>
  </UiDialog>
</template>

<style scoped>
.workspace-grid{display:grid;grid-template-columns:300px minmax(0,1fr);min-height:590px}.workspace-config{padding:17px;border-inline-end:1px solid var(--line);background:var(--soft);overflow:auto}.workspace-results{padding:18px;overflow:auto;background:var(--panel)}.workspace-section{display:grid;gap:8px;margin-bottom:18px}.workspace-section h3{margin:0;font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}.workspace-status{margin:0;font-size:.8125rem;color:var(--muted)}.workspace-status[data-state=ready]{color:var(--tone-ok-fg)}.workspace-status[data-state=error]{color:var(--tone-danger-fg)}.preset-row,.field-actions,.queue-tools,.record-actions,.footer-actions{display:flex;gap:6px;flex-wrap:wrap;align-items:center}.field-actions>span{font-size:.8125rem;color:var(--muted)}.field-group{display:grid;gap:2px;border:1px solid var(--line);border-radius:9px;background:var(--card);overflow:hidden;margin-top:8px}.field-group h4{margin:0;padding:7px 8px;border-bottom:1px solid var(--line);background:var(--soft);font-size:.75rem;color:var(--muted)}.check-item{display:flex;align-items:flex-start;gap:7px;padding:6px 8px;font-size:.8125rem}.check-item small{margin-inline-start:auto;color:var(--tone-warn-fg)}.instruction-field{display:grid;gap:5px;font-size:.8125rem;font-weight:700}.instruction-field textarea{min-height:86px}.queue-header{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;margin-bottom:10px}.queue-header>div:first-child{display:grid;gap:3px}.queue-header span{font-size:.8125rem;color:var(--muted)}.queue-card{border:1px solid var(--line);border-radius:11px;background:var(--card);overflow:hidden;margin-bottom:8px}.queue-card.active{border-color:var(--tone-ok-edge);box-shadow:0 0 0 3px color-mix(in srgb,var(--tone-ok-border) 12%,transparent)}.queue-card.error{border-color:var(--tone-danger-edge)}.queue-summary{width:100%;display:grid;grid-template-columns:30px minmax(0,1fr) auto 20px;gap:9px;align-items:center;text-align:start;border:0;background:var(--card);color:var(--text);padding:11px 12px;cursor:pointer}.queue-summary:hover{background:var(--soft)}.queue-index{display:grid;place-items:center;width:25px;height:25px;border-radius:999px;background:var(--soft);color:var(--muted);font-weight:800}.queue-summary b,.queue-summary small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.queue-summary small{margin-top:2px;color:var(--muted);font-size:.8125rem}.queue-status{font-size:.8125rem;color:var(--muted);white-space:nowrap}.queue-body{padding:12px;border-top:1px solid var(--line)}.empty-result{min-height:120px;display:grid;place-items:center;color:var(--muted)}.record-actions{justify-content:flex-end;margin-bottom:8px}.proposal{border-top:1px solid var(--line);padding-top:10px;margin-top:10px}.proposal header{display:flex;justify-content:space-between;gap:8px;font-size:.8125rem}.proposal header small{color:var(--tone-warn-fg)}.proposal-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.proposal-grid>div{min-width:0}.proposal-grid b{font-size:.75rem;text-transform:uppercase;color:var(--muted)}.proposal pre{max-height:180px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;margin:4px 0 0;padding:8px;border:1px solid var(--line);border-radius:7px;background:var(--soft);font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}.proposal p{margin:7px 0 0;color:var(--muted);font-size:.8125rem;line-height:1.45}.llm-error{padding:10px;border:1px solid var(--tone-danger-edge);border-radius:8px;background:var(--tone-danger-bg);color:var(--tone-danger-fg);font-size:.8125rem}.footer-note{margin-inline-end:auto;color:var(--muted);font-size:.8125rem}.auto-improve-running{min-height:420px;display:grid;place-content:center;justify-items:center;gap:10px;text-align:center}.auto-improve-running h3,.auto-improve-running p{margin:0}.batch-progress-bar{width:min(560px,90%);height:7px;border-radius:999px;background:var(--soft);overflow:hidden}.batch-progress-bar i{display:block;height:100%;background:var(--accent)}
@media(max-width:900px){.workspace-grid{grid-template-columns:1fr}.workspace-config{border-inline-end:0;border-bottom:1px solid var(--line);max-height:none}.proposal-grid{grid-template-columns:1fr}}@media(max-width:700px){.queue-header{display:grid}.queue-summary{grid-template-columns:28px minmax(0,1fr) auto}.queue-status{grid-column:2/4}.workspace-results{padding:12px}}
</style>
