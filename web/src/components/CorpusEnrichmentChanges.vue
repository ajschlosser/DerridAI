<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

interface Replaced { field: string; previous: unknown; value: unknown }
interface Candidate { candidate_id?: string; value: unknown; source?: string; model?: string|null; run_id?: string|null; pass?: number|null; confidence?: number|null; verification_status?: string|null }
interface Dispute { field: string; existing: unknown; proposed: unknown; candidates?: Candidate[]; resolved_at?: string|null }
interface Informational { kind?: string; field?: string; authoritative_value?: unknown; proposed_value?: unknown; confidence?: number; reason?: string; model?: string|null; pass?: number }
interface HistoryEntry { run_id?: string; pass?: number; model?: string; outcome?: string; added_fields?: string[]; replaced?: Replaced[]; disputes?: Dispute[]; informational?: Informational[] }

const props=defineProps<{record:Record<string,unknown>;busy?:boolean}>();
const emit=defineEmits<{resolve:[field:string,value:unknown]}>();
const i18n=useI18nStore();
const owned=new Set(["human_confirmed","human_override","human_confirmed_absent"]);
const stateOf=(field:string)=>String(((props.record.metadata_field_status as Record<string,{status?:string}>|undefined)?.[field]?.status)??"");
const last=computed<HistoryEntry|null>(()=>{const history=(props.record.metadata_enrichment_history as HistoryEntry[]|undefined)??[];return history.length?[...history].reverse()[0]??null:null});
const added=computed(()=>(last.value?.added_fields??[]).filter(field=>!owned.has(stateOf(field))));
const replaced=computed(()=>(last.value?.replaced??[]).filter(item=>!owned.has(stateOf(item.field))));
const disputes=computed<Dispute[]>(()=>{
  const authoritative=((props.record.metadata_disputes as Dispute[]|undefined)??[]).filter(item=>!item.resolved_at&&!owned.has(stateOf(item.field)));
  return authoritative.length?authoritative:(last.value?.disputes??[]).filter(item=>!owned.has(stateOf(item.field)));
});
const informational=computed<Informational[]>(()=>last.value?.informational??[]);
const visible=computed(()=>added.value.length+replaced.value.length+disputes.value.length+informational.value.length>0);
const label=(field:string)=>i18n.t(`record.${field}`,field.replaceAll("_"," "));
const candidatesFor=(item:Dispute):Candidate[]=>item.candidates?.length?item.candidates:[{value:item.existing,source:"current"},{value:item.proposed,source:"proposed"}];
function show(value:unknown):string{if(value===true)return i18n.t("ui.yes","Yes");if(value===false)return i18n.t("ui.no","No");if(Array.isArray(value))return value.join(", ")||"—";return value===null||value===undefined||value===""?"—":String(value)}
function candidateMeta(candidate:Candidate):string{const parts:string[]=[];if(candidate.source==="current")parts.push(i18n.t("pdf_corpus.change_current_value","Current value"));else if(candidate.model)parts.push(String(candidate.model));else if(candidate.source==="llm")parts.push(i18n.t("pdf_corpus.ownership.llm","LLM source"));else if(candidate.source)parts.push(String(candidate.source));if(candidate.pass)parts.push(i18n.tf("pdf_corpus.enrichment_pass_number","pass {pass}",{pass:candidate.pass}));if(typeof candidate.confidence==="number")parts.push(`${Math.round(candidate.confidence*100)}%`);return parts.join(" · ")}
function actionLabel(candidate:Candidate):string{return candidate.source==="current"?i18n.t("pdf_corpus.change_keep_current","Keep current"):i18n.t("pdf_corpus.change_use_value","Use this value")}
function informationalLabel(item:Informational):string{
  if(item.kind==="protected_suggestion")return i18n.t("pdf_corpus.enrichment_protected_suggestion","Protected value retained");
  if(item.kind==="duplicate")return i18n.t("pdf_corpus.enrichment_duplicate","Duplicate candidate");
  return i18n.t("pdf_corpus.enrichment_agreement","No new supported value");
}
function showInformational(item:Informational):string{
  const field=label(String(item.field||""));
  if(item.kind==="protected_suggestion")return `${field}: ${show(item.proposed_value)}`;
  return field;
}
</script>

<template>
<section v-if="visible" class="enrichment-changes" aria-labelledby="enrichment-changes-title">
<header><h4 id="enrichment-changes-title">{{i18n.t("pdf_corpus.enrichment_changes_title","Changed by enrichment")}}</h4><p>{{i18n.t("pdf_corpus.enrichment_changes_help","Unresolved candidates preserve model, pass, and confidence provenance until you decide the field.")}}</p></header>
<ul>
<li v-for="field in added" :key="`a-${field}`" data-kind="added"><span class="kind">{{i18n.t("pdf_corpus.change_added","Added")}}</span><span class="what"><b>{{label(field)}}</b>: {{show(record[field])}}</span></li>
<li v-for="item in replaced" :key="`r-${item.field}`" data-kind="replaced"><span class="kind">{{i18n.t("pdf_corpus.change_replaced","Replaced")}}</span><span class="what"><b>{{label(item.field)}}</b>: <s>{{show(item.previous)}}</s> → {{show(item.value)}}</span><button type="button" class="btn small" :disabled="busy" @click="emit('resolve',item.field,item.previous)">{{i18n.t("pdf_corpus.change_restore","Restore previous")}}</button></li>
<li v-for="item in disputes" :key="`d-${item.field}`" data-kind="disputed"><span class="kind">{{i18n.t("pdf_corpus.change_disputed","Disagreement")}}</span><span class="what"><b>{{label(item.field)}}</b></span><div class="candidate-list"><article v-for="(candidate,index) in candidatesFor(item)" :key="candidate.candidate_id||`${item.field}-${index}`" class="candidate" :title="candidate.run_id||undefined"><div class="candidate-copy"><strong>{{show(candidate.value)}}</strong><small v-if="candidateMeta(candidate)">{{candidateMeta(candidate)}}</small></div><button type="button" class="btn small" :disabled="busy" @click="emit('resolve',item.field,candidate.value)">{{actionLabel(candidate)}}</button></article></div></li>
<li v-for="(item,index) in informational" :key="`i-${item.field}-${index}`" data-kind="informational"><span class="kind">{{informationalLabel(item)}}</span><span class="what"><b>{{showInformational(item)}}</b><small v-if="item.model||item.pass||item.confidence!==undefined">{{[item.model,item.pass?`pass ${item.pass}`:null,typeof item.confidence==='number'?`${Math.round(item.confidence*100)}%`:null].filter(Boolean).join(' · ')}}</small><small>{{item.reason}}</small></span></li>
</ul>
</section>
</template>

<style scoped>
.enrichment-changes{display:grid;gap:8px;padding:12px 14px;border:1px solid var(--tone-info-border);border-radius:12px;background:var(--tone-info-bg);color:var(--text)}h4{margin:0;font-size:.9375rem;color:var(--tone-info-fg)}header p{margin:2px 0 0;font-size:.8125rem;color:var(--text-2);line-height:1.4}ul{display:grid;gap:6px;margin:0;padding:0;list-style:none}li{display:grid;grid-template-columns:max-content minmax(0,1fr);align-items:baseline;gap:6px 12px;padding:8px 10px;border:1px solid var(--line);border-inline-start-width:4px;border-radius:8px;background:var(--card)}li[data-kind="added"]{border-inline-start-color:var(--tone-ok-edge)}li[data-kind="replaced"]{border-inline-start-color:var(--tone-warn-edge)}li[data-kind="disputed"]{border-inline-start-color:var(--tone-danger-edge)}li[data-kind="informational"]{border-inline-start-color:var(--tone-info-border)}.kind{min-inline-size:5.5rem;font-size:.75rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--text-2)}.what{font-size:.875rem;overflow-wrap:anywhere}.what s{color:var(--muted)}.what small{display:block;color:var(--muted);font-size:.75rem;line-height:1.4}li>.btn,li>.candidate-list{grid-column:2}.candidate-list{display:grid;gap:7px;min-width:0}.candidate{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--soft)}.candidate-copy{display:grid;gap:2px;min-width:0}.candidate-copy strong{overflow-wrap:anywhere}.candidate-copy small{color:var(--muted);font-size:.75rem}.candidate .btn{flex:0 0 auto}@media(max-width:520px){li{grid-template-columns:minmax(0,1fr)}li>.btn,li>.candidate-list{grid-column:1}.candidate{align-items:stretch;flex-direction:column}.candidate .btn{align-self:flex-start}}
</style>
