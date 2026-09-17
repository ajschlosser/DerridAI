<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusRecord, SourceBlock } from "../api/pdfCorpus";

const props=defineProps<{
  record:CorpusRecord;
  sourceBlocks?:SourceBlock[];
  busy?:boolean;
  canMergePrevious?:boolean;
  canMergeNext?:boolean;
  canAccept?:boolean;
}>();
const emit=defineEmits<{close:[];accept:[];reject:[];skip:[];undo:[];merge:[direction:"previous"|"next"]}>();
const i18n=useI18nStore();
const dialog=ref<HTMLElement|null>(null);
const closeButton=ref<HTMLButtonElement|null>(null);
const tab=ref<"data"|"evidence"|"source">("data");
const priorActive=ref<HTMLElement|null>(null);
const state=computed(()=>props.record.review_disposition||(props.record.accepted?"accepted":props.record.rejected?"rejected":"pending"));
const position=computed(()=>{
  const index=Number(props.record.topology_index??-1);
  const total=Number(props.record.topology_count??0);
  return index>=0&&total>0?`${index+1} / ${total}`:"—";
});
const importantFields=["region_type","primary_text","discourse_role","speaker","position_holder","stance","proposition_status","claim_scope","region_author","is_direct_quote","extraction_quality"];
const listFields=["topics","concepts","persons","works_referenced","quoted_speaker","quoted_author","quoted_work"];
const metadata=computed(()=>importantFields.flatMap(key=>{const value=props.record[key];return value===undefined||value===null||value===""?[]:[{key,value:typeof value==="boolean"?(value?i18n.t("ui.yes","Yes"):i18n.t("ui.no","No")):String(value),status:props.record.metadata_field_status?.[key]}]}));
const lists=computed(()=>listFields.flatMap(key=>{const value=props.record[key];return Array.isArray(value)&&value.length?[{key,values:value.map(String)}]:[]}));
const evidence=computed(()=>Object.entries(props.record.metadata_evidence||{}));
const unresolved=computed(()=>Array.from(new Set([...(props.record.metadata_incomplete_fields||[]),...(props.record.metadata_review_fields||[])])));
const blocks=computed(()=>props.sourceBlocks||[]);

function focusables(){
  if(!dialog.value)return [] as HTMLElement[];
  return Array.from(dialog.value.querySelectorAll<HTMLElement>('button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')).filter(node=>node.offsetParent!==null);
}
function handleKeydown(event:KeyboardEvent){
  if(event.key==="Escape"){event.preventDefault();emit("close");return}
  if(event.key!=="Tab")return;
  const nodes=focusables();if(nodes.length<2)return;
  const first=nodes[0],last=nodes[nodes.length-1];
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
}
function preventBackgroundScroll(){document.documentElement.dataset.focusReview="true";document.body.style.overflow="hidden"}
function restoreBackgroundScroll(){delete document.documentElement.dataset.focusReview;document.body.style.overflow=""}
onMounted(()=>{priorActive.value=document.activeElement as HTMLElement|null;preventBackgroundScroll();void nextTick(()=>closeButton.value?.focus({preventScroll:true}))});
onBeforeUnmount(()=>{restoreBackgroundScroll();priorActive.value?.focus?.({preventScroll:true})});
watch(()=>props.record.record_id,()=>{tab.value="data";void nextTick(()=>dialog.value?.querySelector<HTMLElement>(".focus-record-text")?.focus({preventScroll:true}))});
</script>

<template>
  <section ref="dialog" class="focus-review" role="dialog" aria-modal="true" @keydown="handleKeydown" :aria-labelledby="`focus-title-${record.record_id}`">
    <header class="focus-head">
      <div class="focus-title-block">
        <span class="eyebrow">{{i18n.t('pdf_corpus.focus_view','Focus review')}}</span>
        <h2 :id="`focus-title-${record.record_id}`">{{record.record_id}}</h2>
        <div class="focus-facts" aria-label="Record position and source facts">
          <span><b>{{position}}</b> {{i18n.t('pdf_corpus.records','records')}}</span>
          <span>{{i18n.t('pdf_corpus.pages','pp.')}} {{record.page_start??'—'}}–{{record.page_end??'—'}}</span>
          <span>{{Number(record.text_length||String(record.text||'').length).toLocaleString()}} {{i18n.t('pdf_corpus.characters','chars')}}</span>
          <span class="state-pill" :data-state="state">{{i18n.t(`pdf_corpus.disposition.${state}`,state)}}</span>
        </div>
      </div>
      <button ref="closeButton" class="btn" type="button" @click="emit('close')">{{i18n.t('ui.close','Close')}}</button>
    </header>

    <main class="focus-workspace">
      <article class="focus-record" aria-labelledby="focus-record-heading">
        <div class="focus-record-heading">
          <div><span class="eyebrow">{{i18n.t('pdf_corpus.proposed_record','Proposed record')}}</span><h3 id="focus-record-heading">{{i18n.t('pdf_corpus.read_record','Read the record')}}</h3></div>
          <div v-if="unresolved.length" class="unresolved-badge">{{unresolved.length}} {{i18n.t('pdf_corpus.unresolved_fields','unresolved fields')}}</div>
        </div>
        <aside v-if="record.review_reason" class="review-reason" role="note"><b>{{i18n.t('pdf_corpus.why_review','Why review')}}</b><span>{{record.review_reason}}</span></aside>
        <div class="focus-record-text" tabindex="-1">{{record.text}}</div>
      </article>

      <aside class="focus-data" :aria-label="i18n.t('pdf_corpus.record_data','Record data')">
        <div class="tabs" role="tablist" :aria-label="i18n.t('pdf_corpus.focus_detail_tabs','Record detail views')">
          <button type="button" role="tab" :aria-selected="tab==='data'" @click="tab='data'">{{i18n.t('pdf_corpus.data_tab','Data')}}</button>
          <button type="button" role="tab" :aria-selected="tab==='evidence'" @click="tab='evidence'">{{i18n.t('pdf_corpus.evidence_tab','Evidence')}}</button>
          <button type="button" role="tab" :aria-selected="tab==='source'" @click="tab='source'">{{i18n.t('pdf_corpus.source_tab','Source')}}</button>
        </div>

        <div v-if="tab==='data'" class="tab-panel" role="tabpanel">
          <div v-if="unresolved.length" class="field-warning" role="status"><b>{{i18n.t('pdf_corpus.metadata_attention','Metadata attention')}}</b><span>{{unresolved.map(key=>i18n.t(`record.${key}`,key.replace(/_/g,' '))).join(', ')}}</span></div>
          <dl v-if="metadata.length" class="metadata-grid">
            <template v-for="item in metadata" :key="item.key">
              <dt>{{i18n.t(`record.${item.key}`,item.key.replace(/_/g,' '))}}</dt>
              <dd><span>{{item.value}}</span><small v-if="item.status" class="provenance-chip" :data-status="item.status.status">{{i18n.t(`pdf_corpus.field_status.${item.status.status}`,String(item.status.status||'').replace(/_/g,' '))}}</small></dd>
            </template>
          </dl>
          <div v-for="item in lists" :key="item.key" class="list-field"><b>{{i18n.t(`record.${item.key}`,item.key.replace(/_/g,' '))}}</b><div><span v-for="value in item.values" :key="value">{{value}}</span></div></div>
        </div>

        <div v-else-if="tab==='evidence'" class="tab-panel evidence-panel" role="tabpanel">
          <article v-for="([field,info]) in evidence" :key="field" class="evidence-row"><header><b>{{i18n.t(`record.${field}`,field.replace(/_/g,' '))}}</b><span>{{Math.round(Number(info.confidence||0)*100)}}%</span></header><p>{{info.reason||i18n.t('pdf_corpus.no_evidence_reason','No evidence rationale recorded.')}}</p><small>{{(info.block_ids||[]).join(', ')||i18n.t('pdf_corpus.no_bound_blocks','No bound source blocks')}}</small></article>
          <p v-if="!evidence.length" class="empty-note">{{i18n.t('pdf_corpus.no_field_evidence','No field-level evidence has been recorded for this proposal.')}}</p>
        </div>

        <div v-else class="tab-panel source-panel" role="tabpanel">
          <article v-for="block in blocks" :key="block.block_id" class="source-row"><header><b>{{block.block_id}}</b><span>PDF {{block.page}} · {{block.type}}</span></header><p>{{block.text}}</p></article>
          <p v-if="!blocks.length" class="empty-note">{{i18n.t('pdf_corpus.source_loading_or_unavailable','Source blocks are loading or unavailable.')}}</p>
        </div>
      </aside>
    </main>

    <p v-if="canAccept===false" id="focus-metadata-blocker" class="focus-blocker" role="status">{{i18n.t('pdf_corpus.resolve_metadata_before_accept','Resolve uncertain metadata before accepting this record.')}}</p>
    <footer class="focus-actions" :aria-label="i18n.t('pdf_corpus.record_decision','Record decision')">
      <div class="structural-actions"><button class="btn" type="button" @click="emit('merge','previous')" :disabled="busy||!canMergePrevious">{{i18n.t('pdf_corpus.merge_previous','Merge previous')}}</button><button class="btn" type="button" @click="emit('merge','next')" :disabled="busy||!canMergeNext">{{i18n.t('pdf_corpus.merge_next','Merge next')}}</button><button class="btn" type="button" @click="emit('undo')" :disabled="busy">{{i18n.t('pdf_corpus.undo','Undo')}}</button></div>
      <div class="decision-actions"><button class="btn" type="button" @click="emit('skip')" :disabled="busy">{{i18n.t('pdf_corpus.skip','Skip')}}</button><button class="btn danger" type="button" @click="emit('reject')" :disabled="busy">{{i18n.t('pdf_corpus.reject_next','Reject & next')}}</button><button class="btn primary" type="button" @click="emit('accept')" :disabled="busy||canAccept===false" :aria-describedby="canAccept===false?'focus-metadata-blocker':undefined">{{i18n.t('pdf_corpus.accept_next','Accept & next')}}</button></div>
    </footer>
  </section>
</template>

<style scoped>
.focus-review{position:fixed;inset:0;z-index:10000;background:var(--bg);display:grid;grid-template-rows:auto minmax(0,1fr) auto;color:var(--text)}
.focus-head{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;padding:18px clamp(18px,3vw,42px);border-bottom:1px solid var(--line);background:var(--card)}.focus-title-block{display:grid;gap:5px;min-width:0}.focus-head h2{margin:0;font-size:20px;overflow-wrap:anywhere}.eyebrow{font-size:9px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:800}.focus-facts{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:10px;color:var(--muted)}.state-pill,.unresolved-badge,.provenance-chip{border:1px solid var(--line);border-radius:999px;padding:3px 7px;font-size:9px;font-weight:750}.state-pill[data-state="accepted"],.provenance-chip[data-status="human_confirmed"],.provenance-chip[data-status="deterministic"]{background:#edf8f1;color:#245f3d}.state-pill[data-state="rejected"],.provenance-chip[data-status="invalid"]{background:#fff1f1;color:#7d2222}.provenance-chip[data-status="unresolved"]{background:#fff8e9;color:#604300}
.focus-workspace{min-height:0;display:grid;grid-template-columns:minmax(0,1fr) minmax(320px,400px);gap:0;overflow:hidden}.focus-record{min-width:0;min-height:0;overflow:auto;border-inline-end:1px solid var(--line);background:var(--card)}.focus-record-heading{position:sticky;top:0;z-index:2;background:var(--card);display:flex;justify-content:space-between;align-items:center;gap:16px;padding:14px clamp(22px,4vw,54px);border-bottom:1px solid var(--line)}.focus-record-heading h3{margin:2px 0 0;font-size:14px}.unresolved-badge{background:#fff8e9;color:#604300}.review-reason{display:grid;gap:4px;max-width:86ch;margin:18px auto 0;padding:11px 14px;border-radius:10px;background:#fff8e9;color:#604300;font-size:11px}.focus-record-text{max-width:78ch;margin:0 auto;padding:34px clamp(24px,5vw,72px) 80px;white-space:pre-wrap;font:18px/1.78 Georgia,serif;outline:none}
.focus-data{min-width:0;min-height:0;overflow:auto;background:var(--soft)}.tabs{position:sticky;top:0;z-index:3;display:grid;grid-template-columns:repeat(3,1fr);background:var(--card);border-bottom:1px solid var(--line)}.tabs button{min-height:44px;border:0;border-inline-end:1px solid var(--line);background:transparent;color:inherit;font-size:10px;font-weight:750;cursor:pointer}.tabs button[aria-selected="true"]{box-shadow:inset 0 -3px 0 var(--accent);background:var(--soft)}.tab-panel{padding:16px;display:grid;gap:12px}.field-warning{display:grid;gap:3px;padding:10px 12px;border:1px solid #d9bf76;border-radius:9px;background:#fff8e9;font-size:10px}.metadata-grid{display:grid;grid-template-columns:minmax(110px,.8fr) minmax(0,1.2fr);gap:0;margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card)}.metadata-grid dt,.metadata-grid dd{padding:10px 11px;border-bottom:1px solid var(--line)}.metadata-grid dt{font-size:9px;color:var(--muted);font-weight:700}.metadata-grid dd{margin:0;display:flex;justify-content:space-between;align-items:flex-start;gap:8px;font-size:10px;overflow-wrap:anywhere}.metadata-grid dt:nth-last-of-type(1),.metadata-grid dd:last-child{border-bottom:0}.list-field{display:grid;gap:7px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--card)}.list-field>b{font-size:9px}.list-field>div{display:flex;flex-wrap:wrap;gap:5px}.list-field span{padding:4px 7px;border-radius:999px;background:var(--soft);font-size:9px}.evidence-row,.source-row{border:1px solid var(--line);border-radius:9px;background:var(--card);padding:10px}.evidence-row header,.source-row header{display:flex;justify-content:space-between;gap:8px;font-size:9px}.evidence-row p{margin:7px 0;font-size:10px;line-height:1.45}.evidence-row small{font-size:8px;color:var(--muted)}.source-row p{white-space:pre-wrap;margin:8px 0 0;font:13px/1.55 Georgia,serif}.source-row header span{font-size:8px;color:var(--muted)}.empty-note{margin:0;color:var(--muted);font-size:10px;line-height:1.5}
.focus-blocker{margin:0;padding:8px 18px;border-top:1px solid #d9bf76;background:#fff8e9;color:#604300;font-size:10px}.focus-actions{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px clamp(18px,3vw,42px);border-top:1px solid var(--line);background:var(--card)}.structural-actions,.decision-actions{display:flex;gap:8px;flex-wrap:wrap}.danger{border-color:#a13f3f;color:#7d2222}.focus-review :is(button,[tabindex]):focus-visible{outline:3px solid var(--accent);outline-offset:2px}
@media(max-width:1000px){.focus-workspace{grid-template-columns:minmax(0,1fr) 330px}.focus-record-text{font-size:17px;padding-inline:28px}}@media(max-width:760px){.focus-workspace{grid-template-columns:1fr;overflow:auto}.focus-record{overflow:visible;border-inline-end:0}.focus-data{overflow:visible;border-top:1px solid var(--line)}.focus-blocker{margin:0;padding:8px 18px;border-top:1px solid #d9bf76;background:#fff8e9;color:#604300;font-size:10px}.focus-actions{align-items:stretch;flex-direction:column}.decision-actions{justify-content:flex-end}.focus-record-text{font-size:16px;padding:24px 18px 50px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style>
