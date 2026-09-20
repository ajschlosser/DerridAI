<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";

const props=defineProps<{build:CorpusBuild;busy?:boolean}>();
const emit=defineEmits<{retry:[];review:[recordId:string]}>();
const i18n=useI18nStore();
const summary=computed(()=>props.build.metadata_issue_summary||{});
const issues=computed(()=>summary.value.issues||[]);
const retryable=computed(()=>issues.value.filter(issue=>issue.retryable));
const human=computed(()=>issues.value.filter(issue=>!issue.retryable));
const model=computed(()=>String(props.build.model||"—"));
const provider=computed(()=>String((props.build.request as Record<string,unknown>|undefined)?.provider_profile_id||props.build.provider||"—"));
const operation=computed(()=>props.build.metadata_operation||{});
const operationRunning=computed(()=>["queued","running"].includes(String(operation.value.state||"")));
const progress=computed(()=>{
  const total=Math.max(1,Number(operation.value.fields_total||0));
  return Math.max(0,Math.min(100,Math.round(Number(operation.value.fields_resolved||0)/total*100)));
});
const firstHumanRecord=computed(()=>String(human.value.find(issue=>issue.record_id)?.record_id||""));
const totalIssues=computed(()=>Number(summary.value.fields_unresolved??issues.value.length));
function reasonLabel(code?:string){return i18n.t(`pdf_corpus.metadata_reason.${code||'unresolved'}`,String(code||"unresolved").replace(/_/g," "))}
</script>

<template>
  <section v-if="totalIssues>0" class="metadata-issues" aria-labelledby="metadata-resolution-title">
    <header class="resolution-head">
      <div>
        <span class="eyebrow">{{i18n.t('pdf_corpus.metadata_resolution','Metadata resolution')}}</span>
        <h3 id="metadata-resolution-title">{{i18n.t('pdf_corpus.metadata_needs_attention','Metadata needs attention')}}</h3>
        <p>{{i18n.tf('pdf_corpus.metadata_resolution_intro','Corpus construction and record review can be complete while required scholarly metadata remains unresolved. {records} record(s) contain {fields} required field issue(s).',{records:Number(summary.records_incomplete||0),fields:Number(summary.fields_unresolved||0)})}}</p>
      </div>
      <div class="resolution-count" aria-label="Metadata issue count"><strong>{{summary.fields_unresolved||0}}</strong><span>{{i18n.t('pdf_corpus.fields_to_resolve','fields to resolve')}}</span></div>
    </header>

    <section v-if="operationRunning||operation.state==='completed'||operation.state==='failed'" class="operation" :data-state="operation.state" role="status" aria-live="polite">
      <div class="operation-copy">
        <b>{{operationRunning?i18n.t('pdf_corpus.metadata_retry_running','Retrying automatically resolvable metadata'):operation.state==='completed'?i18n.t('pdf_corpus.metadata_retry_complete','Metadata retry complete'):i18n.t('pdf_corpus.metadata_retry_failed','Metadata retry failed')}}</b>
        <span v-if="operationRunning">{{i18n.tf('pdf_corpus.metadata_retry_progress','{processed} of {total} records processed · {resolved} fields resolved',{processed:Number(operation.records_processed||0),total:Number(operation.records_total||0),resolved:Number(operation.fields_resolved||0)})}}</span>
        <span v-else-if="operation.state==='completed'">{{i18n.tf('pdf_corpus.metadata_retry_result','{resolved} fields resolved · {remaining} fields still need attention',{resolved:Number(operation.fields_resolved||0),remaining:Number(operation.fields_remaining||0)})}}</span>
        <span v-else>{{operation.error||i18n.t('pdf_corpus.metadata_retry_failed_help','The retry stopped without changing successful metadata. Review the remaining issue queue or try again after correcting the provider.')}}</span>
      </div>
      <progress v-if="operationRunning" :value="progress" max="100">{{progress}}%</progress>
    </section>

    <div class="resolution-paths">
      <article class="resolution-path" :data-empty="retryable.length===0">
        <span class="path-kicker">{{i18n.t('pdf_corpus.automatic_resolution','Automatic resolution')}}</span>
        <h4>{{i18n.tf('pdf_corpus.retryable_metadata_fields','{count} field(s) can be retried',{count:Number(summary.auto_retry_fields??retryable.length)})}}</h4>
        <p>{{i18n.t('pdf_corpus.retryable_metadata_help','These issues came from a failed/invalid model response or evidence threshold. Retrying affects only unresolved records; completed metadata and topology are preserved.')}}</p>
        <div class="execution"><span>{{i18n.t('pdf_corpus.provider_profile','Provider profile')}} <code>{{provider}}</code></span><span>{{i18n.t('pdf_corpus.model','Model')}} <code>{{model}}</code></span></div>
        <button v-if="Number(summary.auto_retry_fields??retryable.length)>0" type="button" class="btn primary" :disabled="busy||operationRunning" @click="emit('retry')">{{operationRunning?i18n.t('pdf_corpus.retrying_metadata','Retrying metadata…'):i18n.tf('pdf_corpus.retry_fields_with_model','Retry {count} field(s) with {model}',{count:Number(summary.auto_retry_fields??retryable.length),model})}}</button>
        <span v-else class="path-done">{{i18n.t('pdf_corpus.no_automatic_metadata_work','No automatically retryable fields remain.')}}</span>
      </article>

      <article class="resolution-path" :data-empty="human.length===0">
        <span class="path-kicker">{{i18n.t('pdf_corpus.human_resolution','Human resolution')}}</span>
        <h4>{{i18n.tf('pdf_corpus.human_metadata_fields','{count} field(s) require judgment',{count:Number(summary.human_review_fields??human.length)})}}</h4>
        <p>{{i18n.t('pdf_corpus.human_metadata_help','These fields are ambiguous or depend on source quality. Review the proposed record, source evidence, allowed values, and field provenance before confirming a value.')}}</p>
        <button v-if="firstHumanRecord" type="button" class="btn" :disabled="busy" @click="emit('review',firstHumanRecord)">{{i18n.t('pdf_corpus.review_ambiguous_metadata','Review ambiguous metadata')}}</button>
        <span v-else class="path-done">{{i18n.t('pdf_corpus.no_human_metadata_work','No metadata fields require human judgment.')}}</span>
      </article>
    </div>

    <details v-if="issues.length" class="issue-details">
      <summary>{{i18n.tf('pdf_corpus.view_metadata_issue_details','View {count} metadata issue(s)',{count:issues.length})}}</summary>
      <div class="issue-table" role="table" :aria-label="i18n.t('pdf_corpus.metadata_issue_table','Metadata issue details')">
        <div class="issue-row issue-header" role="row"><span role="columnheader">{{i18n.t('pdf_corpus.record','Record')}}</span><span role="columnheader">{{i18n.t('pdf_corpus.field','Field')}}</span><span role="columnheader">{{i18n.t('pdf_corpus.reason','Reason')}}</span><span role="columnheader">{{i18n.t('pdf_corpus.next_step','Next step')}}</span></div>
        <button v-for="issue in issues" :key="`${issue.record_id}-${issue.field}`" type="button" class="issue-row" role="row" @click="issue.record_id&&emit('review',String(issue.record_id))">
          <span role="cell"><b>{{issue.record_id}}</b><small>{{i18n.t('pdf_corpus.pages','pp.')}} {{issue.page_start??'—'}}–{{issue.page_end??'—'}}</small></span>
          <span role="cell">{{i18n.t(`record.${issue.field}`,String(issue.field||'').replace(/_/g,' '))}}</span>
          <span role="cell">{{reasonLabel(issue.issue_type)}}<small v-if="issue.reason">{{issue.reason}}</small></span>
          <span role="cell">{{issue.retryable?i18n.t('pdf_corpus.retry_automatically','Retry automatically'):i18n.t('pdf_corpus.review_manually','Review manually')}}</span>
        </button>
      </div>
    </details>
  </section>
</template>

<style scoped>
.metadata-issues{display:grid;gap:14px;padding:16px;border:1px solid var(--tone-warn-edge);border-radius:12px;background:var(--tone-warn-bg)}.resolution-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}.resolution-head h3{margin:2px 0 5px;font-size:1rem}.resolution-head p{margin:0;max-width:76ch;font-size:.8125rem;line-height:1.5;color:var(--tone-warn-fg)}.eyebrow,.path-kicker{font-size:.8125rem;text-transform:uppercase;letter-spacing:.08em;color:var(--tone-warn-fg);font-weight:800}.resolution-count{display:grid;text-align:end;min-width:90px}.resolution-count strong{font-size:1.5rem;line-height:1}.resolution-count span{font-size:.8125rem;color:var(--muted)}.operation{display:grid;grid-template-columns:minmax(0,1fr) minmax(160px,.45fr);gap:14px;align-items:center;padding:11px 12px;border-radius:9px;background:var(--card);border:1px solid var(--line)}.operation[data-state="failed"]{border-color:var(--tone-danger-border);background:var(--tone-danger-bg)}.operation-copy{display:grid;gap:3px}.operation-copy b{font-size:.8125rem}.operation-copy span{font-size:.8125rem;color:var(--muted);line-height:1.45}.operation progress{width:100%;height:8px}.resolution-paths{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.resolution-path{display:grid;align-content:start;gap:8px;padding:13px;border:1px solid color-mix(in srgb,var(--tone-warn-fg) 24%,transparent);border-radius:10px;background:color-mix(in srgb,var(--card) 58%,transparent)}.resolution-path[data-empty="true"]{opacity:.78}.resolution-path h4{margin:0;font-size:.8125rem}.resolution-path p{margin:0;font-size:.8125rem;line-height:1.5;color:var(--muted)}.execution{display:flex;gap:13px;flex-wrap:wrap;font-size:.8125rem;color:var(--muted)}.execution code{color:var(--text)}.resolution-path .btn{justify-self:start}.path-done{font-size:.8125rem;color:var(--muted)}.issue-details{font-size:.8125rem}.issue-details summary{cursor:pointer;font-weight:800}.issue-table{display:grid;margin-top:8px;border:1px solid var(--line);border-radius:9px;overflow:hidden}.issue-row{display:grid;grid-template-columns:minmax(130px,.8fr) minmax(120px,.7fr) minmax(220px,1.5fr) minmax(130px,.7fr);gap:10px;align-items:start;padding:8px 10px;border:0;border-bottom:1px solid var(--line);background:var(--card);color:inherit;text-align:start;font:inherit}.issue-row:not(.issue-header){cursor:pointer}.issue-row:not(.issue-header):hover{background:var(--soft)}.issue-row:last-child{border-bottom:0}.issue-header{font-weight:800;background:var(--soft)}.issue-row span{display:grid;gap:2px}.issue-row small{font-size:.8125rem;color:var(--muted);line-height:1.35}@media(max-width:800px){.resolution-head{display:grid}.resolution-count{text-align:start}.resolution-paths{grid-template-columns:1fr}.operation{grid-template-columns:1fr}.issue-row{grid-template-columns:1fr 1fr}.issue-header{display:none}}
</style>
