<script setup lang="ts">
import { computed } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";

const props=defineProps<{build:CorpusBuild;busy?:boolean}>();
const emit=defineEmits<{retryMetadata:[];reviewMetadata:[];reviewRejected:[];publish:[]}>();
const i18n=useI18nStore();
const readiness=computed(()=>props.build.publication_readiness||{});
const summary=computed(()=>props.build.metadata_issue_summary||{});
const publication=computed(()=>props.build.publication||null);
const next=computed(()=>String(readiness.value.next_action||"inspect"));
const blockers=computed(()=>readiness.value.blockers||[]);
const validation=computed(()=>props.build.validation||{});
const sourceQuality=computed(()=>props.build.source_quality||{});
const primaryLabel=computed(()=>{
  if(publication.value)return i18n.t('pdf_corpus.download_jsonl','Download JSONL');
  if(next.value==='resolve_metadata')return i18n.t('pdf_corpus.resolve_metadata_issues','Resolve metadata issues');
  if(next.value==='resolve_rejections')return i18n.t('pdf_corpus.review_rejected_records','Review rejected records');
  if(next.value==='resolve_validation')return i18n.t('pdf_corpus.review_validation_issues','Review validation issues');
  if(next.value==='publish')return i18n.t('pdf_corpus.publish_corpus','Publish corpus');
  return i18n.t('pdf_corpus.inspect_remaining_work','Inspect remaining work');
});
function act(){
  if(next.value==='resolve_metadata')emit('reviewMetadata');
  else if(next.value==='resolve_rejections')emit('reviewRejected');
  else if(next.value==='publish')emit('publish');
}
function blockerLabel(code?:string){return i18n.t(`pdf_corpus.readiness_blocker.${code||'unknown'}`,String(code||'unknown').replace(/_/g,' '))}
</script>

<template>
  <section class="finish-workspace" aria-labelledby="finish-corpus-title">
    <header class="finish-head">
      <div>
        <span class="eyebrow">{{i18n.t('pdf_corpus.finish_phase','Finish corpus')}}</span>
        <h2 id="finish-corpus-title">{{publication?i18n.t('pdf_corpus.published_revision','Published revision'):readiness.can_publish?i18n.t('pdf_corpus.ready_to_publish','Ready to publish'):i18n.t('pdf_corpus.finish_corpus_title','Finish corpus')}}</h2>
        <p>{{publication?i18n.t('pdf_corpus.finish_published_help','This immutable publication snapshot is complete. Editing the draft creates a new unpublished revision.'):readiness.can_publish?i18n.t('pdf_corpus.finish_ready_help','Record review, required metadata, source fidelity, and publication validation have passed.'):i18n.t('pdf_corpus.finish_blocked_help','Record review is complete. Resolve the remaining publication blockers below; DerridAI will then enable publication automatically.')}}</p>
      </div>
      <div class="finish-primary">
        <a v-if="publication" class="btn primary" :href="`/api/pdf/publications/${encodeURIComponent(publication.publication_id)}/download`">{{primaryLabel}}</a>
        <button v-else type="button" class="btn primary" :disabled="busy||!['resolve_metadata','resolve_rejections','publish'].includes(next)" @click="act">{{primaryLabel}}</button>
      </div>
    </header>

    <div class="finish-grid">
      <article class="finish-card" data-state="complete">
        <span class="card-state">{{i18n.t('pdf_corpus.complete','Complete')}}</span>
        <h3>{{i18n.t('pdf_corpus.record_review','Record review')}}</h3>
        <dl><div><dt>{{i18n.t('pdf_corpus.reviewed','Reviewed')}}</dt><dd>{{readiness.records_reviewed||0}} / {{readiness.records_total||0}}</dd></div><div><dt>{{i18n.t('pdf_corpus.accepted_label','Accepted')}}</dt><dd>{{readiness.records_accepted||0}}</dd></div><div><dt>{{i18n.t('pdf_corpus.rejected','Rejected')}}</dt><dd>{{readiness.records_rejected||0}}</dd></div><div><dt>{{i18n.t('pdf_corpus.pending','Pending')}}</dt><dd>{{readiness.records_pending||0}}</dd></div></dl>
        <button v-if="Number(readiness.records_rejected||0)>0" type="button" class="link-action" @click="emit('reviewRejected')">{{i18n.t('pdf_corpus.review_rejected_records','Review rejected records')}}</button>
      </article>

      <article class="finish-card" :data-state="Number(summary.fields_unresolved||0)>0?'attention':'complete'">
        <span class="card-state">{{Number(summary.fields_unresolved||0)>0?i18n.t('pdf_corpus.attention_required','Attention required'):i18n.t('pdf_corpus.complete','Complete')}}</span>
        <h3>{{i18n.t('pdf_corpus.required_metadata','Required metadata')}}</h3>
        <p v-if="Number(summary.fields_unresolved||0)>0">{{i18n.tf('pdf_corpus.finish_metadata_summary','{records} record(s) contain {fields} unresolved required field(s).',{records:Number(summary.records_incomplete||0),fields:Number(summary.fields_unresolved||0)})}}</p>
        <p v-else>{{i18n.t('pdf_corpus.finish_metadata_complete','All publication-required metadata fields are resolved and validated.')}}</p>
        <dl><div><dt>{{i18n.t('pdf_corpus.auto_retry','Auto retry')}}</dt><dd>{{summary.auto_retry_fields||0}}</dd></div><div><dt>{{i18n.t('pdf_corpus.human_review','Human review')}}</dt><dd>{{summary.human_review_fields||0}}</dd></div></dl>
        <div v-if="Number(summary.fields_unresolved||0)>0" class="card-actions"><button type="button" class="btn" @click="emit('reviewMetadata')">{{i18n.t('pdf_corpus.open_metadata_queue','Open metadata queue')}}</button><button v-if="Number(summary.auto_retry_fields||0)>0" type="button" class="btn" :disabled="busy" @click="emit('retryMetadata')">{{i18n.tf('pdf_corpus.retry_metadata_fields','Retry {count} field(s)',{count:Number(summary.auto_retry_fields||0)})}}</button></div>
      </article>

      <article class="finish-card" :data-state="validation.valid?'complete':'attention'">
        <span class="card-state">{{validation.valid?i18n.t('pdf_corpus.complete','Complete'):i18n.t('pdf_corpus.attention_required','Attention required')}}</span>
        <h3>{{i18n.t('pdf_corpus.final_validation','Final validation')}}</h3>
        <dl><div><dt>{{i18n.t('pdf_corpus.source_fidelity','Source fidelity')}}</dt><dd>{{validation.source_valid?i18n.t('pdf_corpus.passed','Passed'):i18n.t('pdf_corpus.needs_attention','Needs attention')}}</dd></div><div><dt>{{i18n.t('pdf_corpus.metadata_validation','Metadata validation')}}</dt><dd>{{validation.metadata_valid?i18n.t('pdf_corpus.passed','Passed'):i18n.t('pdf_corpus.needs_attention','Needs attention')}}</dd></div><div><dt>{{i18n.t('pdf_corpus.source_quality','Source quality')}}</dt><dd>{{Number(sourceQuality.blocking_page_count||0)===0?i18n.t('pdf_corpus.passed','Passed'):i18n.tf('pdf_corpus.blocking_pages','{count} blocking page(s)',{count:Number(sourceQuality.blocking_page_count||0)})}}</dd></div><div><dt>{{i18n.t('pdf_corpus.coverage','Coverage')}}</dt><dd>{{Math.round(Number(validation.coverage||0)*100)}}%</dd></div></dl>
      </article>

      <article class="finish-card" :data-state="publication?'complete':readiness.can_publish?'ready':'waiting'">
        <span class="card-state">{{publication?i18n.t('pdf_corpus.complete','Complete'):readiness.can_publish?i18n.t('pdf_corpus.ready','Ready'):i18n.t('pdf_corpus.waiting','Waiting')}}</span>
        <h3>{{i18n.t('pdf_corpus.publication','Publication')}}</h3>
        <p v-if="publication">{{i18n.tf('pdf_corpus.publication_snapshot_summary','Revision published with {count} record(s).',{count:publication.record_count})}}</p>
        <p v-else-if="readiness.can_publish">{{i18n.t('pdf_corpus.publication_ready_help','All required gates have passed. Publication creates an immutable UTF-8 JSONL snapshot.')}}</p>
        <p v-else>{{i18n.t('pdf_corpus.publication_waiting_help','Publication will unlock automatically after the blockers in this Finish corpus view are resolved.')}}</p>
      </article>
    </div>

    <details v-if="blockers.length" class="blockers">
      <summary>{{i18n.tf('pdf_corpus.view_publication_blockers','View {count} publication blocker(s)',{count:blockers.length})}}</summary>
      <ul><li v-for="(blocker,index) in blockers" :key="`${blocker.code}-${index}`"><b>{{blockerLabel(blocker.code)}}</b><span v-if="blocker.count"> · {{blocker.count}}</span></li></ul>
    </details>
  </section>
</template>

<style scoped>
.finish-workspace{display:grid;gap:16px;padding:18px;border:1px solid var(--line);border-radius:13px;background:var(--card)}.finish-head{display:flex;justify-content:space-between;gap:22px;align-items:flex-start}.finish-head h2{margin:3px 0 6px;font-size:20px}.finish-head p{margin:0;max-width:78ch;font-size:.8125rem;line-height:1.55;color:var(--muted)}.eyebrow{font-size:.8125rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}.finish-primary{display:flex;align-items:center}.finish-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.finish-card{display:grid;align-content:start;gap:9px;padding:14px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.finish-card[data-state="attention"]{background:#fffaf0;border-color:#d9bf76}.finish-card[data-state="ready"],.finish-card[data-state="complete"]{background:#edf8f1}.card-state{font-size:.8125rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:800}.finish-card h3{margin:0;font-size:13px}.finish-card p{margin:0;font-size:.8125rem;line-height:1.48;color:var(--muted)}dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin:0}dl div{padding-inline-start:8px;border-inline-start:2px solid var(--line)}dt{font-size:.8125rem;color:var(--muted)}dd{margin:2px 0 0;font-size:.8125rem;font-weight:800}.card-actions{display:flex;gap:7px;flex-wrap:wrap}.link-action{justify-self:start;border:0;background:transparent;color:var(--accent);padding:0;text-decoration:underline;font-size:.8125rem;cursor:pointer}.blockers{font-size:.8125rem}.blockers summary{cursor:pointer;font-weight:800}.blockers ul{margin:8px 0 0;padding-inline-start:20px;color:var(--muted)}@media(max-width:760px){.finish-head{display:grid}.finish-grid{grid-template-columns:1fr}.finish-primary .btn{width:100%}}
</style>
