<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusRecord } from "../api/pdfCorpus";

const props=defineProps<{record:CorpusRecord;busy?:boolean;canMergePrevious?:boolean;canMergeNext?:boolean}>();
const emit=defineEmits<{close:[];accept:[];reject:[];skip:[];undo:[];merge:[direction:"previous"|"next"]}>();
const i18n=useI18nStore();
const dialog=ref<HTMLElement|null>(null);
const state=computed(()=>props.record.review_disposition||(props.record.accepted?"accepted":props.record.rejected?"rejected":"pending"));
const importantFields=["speaker","position_holder","stance","discourse_role","proposition_status","claim_scope","region_type","region_author","is_direct_quote"];
const listFields=["topics","concepts","persons","works_referenced","quoted_speaker","quoted_author","quoted_work"];
const metadata=computed(()=>importantFields.flatMap(key=>{const value=props.record[key];return value===undefined||value===null||value===""?[]:[{key,value:String(value)}]}));
const lists=computed(()=>listFields.flatMap(key=>{const value=props.record[key];return Array.isArray(value)&&value.length?[{key,values:value.map(String)}]:[]}));
const evidenceCount=computed(()=>Object.keys(props.record.metadata_evidence||{}).length);
function handleKeydown(event:KeyboardEvent){
  if(event.key==="Escape"){event.preventDefault();emit("close");return}
  if(event.key!=="Tab"||!dialog.value)return;
  const nodes=Array.from(dialog.value.querySelectorAll<HTMLElement>('button:not([disabled]),[href],[tabindex]:not([tabindex="-1"])')).filter(node=>node.offsetParent!==null);
  if(nodes.length<2)return;const first=nodes[0],last=nodes[nodes.length-1];
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
}
onMounted(()=>void nextTick(()=>dialog.value?.focus({preventScroll:true})));
</script>

<template>
  <section ref="dialog" tabindex="-1" class="focus-review" role="dialog" aria-modal="true" @keydown="handleKeydown" :aria-labelledby="`focus-title-${record.record_id}`">
    <header class="focus-head">
      <div>
        <span class="eyebrow">{{i18n.t('pdf_corpus.focus_view','Focus view')}}</span>
        <h2 :id="`focus-title-${record.record_id}`">{{i18n.t('pdf_corpus.focus_record_title','Review proposed record')}} · {{record.record_id}}</h2>
        <p>{{i18n.t('pdf_corpus.focus_record_help','Judge the proposed record as a scholarly unit. The record text and its interpreted data are kept together so the decision can be made quickly.')}}</p>
      </div>
      <button class="btn" type="button" @click="emit('close')">{{i18n.t('ui.close','Close')}}</button>
    </header>

    <main class="focus-body">
      <article class="record-card">
        <div class="record-status">
          <strong :data-state="state">{{i18n.t(`pdf_corpus.disposition.${state}`,state)}}</strong>
          <span>{{i18n.t('pdf_corpus.pages','pp.')}} {{record.page_start??'—'}}–{{record.page_end??'—'}}</span>
          <span>{{Number(record.text_length||String(record.text||'').length).toLocaleString()}} {{i18n.t('pdf_corpus.characters','chars')}}</span>
          <span>{{record.source_block_ids?.length||0}} {{i18n.t('pdf_corpus.source_blocks','source blocks')}}</span>
          <span>{{evidenceCount}} {{i18n.t('pdf_corpus.evidence_bindings','evidence bindings')}}</span>
        </div>
        <aside v-if="record.review_reason" class="review-reason" role="note"><b>{{i18n.t('pdf_corpus.why_review','Why review')}}</b><span>{{record.review_reason}}</span></aside>
        <div class="record-text">{{record.text}}</div>
      </article>

      <aside class="data-card" :aria-label="i18n.t('pdf_corpus.record_data','Record data')">
        <div class="data-heading"><span class="eyebrow">{{i18n.t('pdf_corpus.record_data','Record data')}}</span><h3>{{i18n.t('pdf_corpus.interpretive_data','Interpretive data')}}</h3></div>
        <dl v-if="metadata.length" class="metadata-grid">
          <template v-for="item in metadata" :key="item.key"><dt>{{i18n.t(`record.${item.key}`,item.key.replace(/_/g,' '))}}</dt><dd>{{item.value}}</dd></template>
        </dl>
        <div v-for="item in lists" :key="item.key" class="list-field"><b>{{i18n.t(`record.${item.key}`,item.key.replace(/_/g,' '))}}</b><div><span v-for="value in item.values" :key="value">{{value}}</span></div></div>
        <details class="provenance"><summary>{{i18n.t('pdf_corpus.provenance','Provenance')}}</summary><dl><dt>{{i18n.t('pdf_corpus.record_revision','Record revision')}}</dt><dd>{{record.record_revision||1}}</dd><dt>{{i18n.t('pdf_corpus.source_blocks','Source blocks')}}</dt><dd>{{record.source_block_ids?.join(', ')||'—'}}</dd><dt>{{i18n.t('pdf_corpus.pdf_pages','PDF pages')}}</dt><dd>{{record.pdf_pages?.join(', ')||'—'}}</dd></dl></details>
      </aside>
    </main>

    <footer class="focus-actions">
      <div class="structural-actions"><button class="btn" type="button" @click="emit('merge','previous')" :disabled="busy||!canMergePrevious">{{i18n.t('pdf_corpus.merge_previous','Merge previous')}}</button><button class="btn" type="button" @click="emit('merge','next')" :disabled="busy||!canMergeNext">{{i18n.t('pdf_corpus.merge_next','Merge next')}}</button><button class="btn" type="button" @click="emit('undo')" :disabled="busy">{{i18n.t('pdf_corpus.undo','Undo')}}</button></div>
      <div class="decision-actions"><button class="btn" type="button" @click="emit('skip')" :disabled="busy">{{i18n.t('pdf_corpus.skip','Skip')}}</button><button class="btn danger" type="button" @click="emit('reject')" :disabled="busy">{{i18n.t('pdf_corpus.reject_next','Reject & next')}}</button><button class="btn primary" type="button" @click="emit('accept')" :disabled="busy">{{i18n.t('pdf_corpus.accept_next','Accept & next')}}</button></div>
    </footer>
  </section>
</template>

<style scoped>
.focus-review{position:fixed;inset:20px;z-index:80;background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 18px 70px rgb(0 0 0/.24);display:grid;grid-template-rows:auto minmax(0,1fr) auto;overflow:hidden}.focus-head{display:flex;justify-content:space-between;gap:20px;padding:16px 18px;border-bottom:1px solid var(--line)}.focus-head h2{margin:2px 0 4px;font-size:20px}.focus-head p{margin:0;max-width:80ch;font-size:10px;color:var(--muted);line-height:1.45}.eyebrow{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.focus-body{min-height:0;overflow:auto;display:grid;grid-template-columns:minmax(0,1.65fr) minmax(300px,.72fr);gap:18px;padding:18px;background:var(--bg)}.record-card,.data-card{background:var(--card);border:1px solid var(--line);border-radius:13px;min-width:0}.record-card{overflow:hidden;align-self:start}.record-status{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 16px;border-bottom:1px solid var(--line);font-size:9px;color:var(--muted)}.record-status strong{color:var(--text);text-transform:uppercase;font-size:9px;letter-spacing:.04em}.record-status strong[data-state="rejected"]{color:#7d2222}.review-reason{display:grid;gap:3px;margin:14px 18px 0;padding:10px 12px;border-radius:9px;background:#fff8e9;color:#604300;font-size:10px}.record-text{padding:26px 30px 34px;white-space:pre-wrap;font:17px/1.7 Georgia,serif;max-width:82ch;margin:auto}.data-card{align-self:start;overflow:hidden}.data-heading{padding:13px 14px;border-bottom:1px solid var(--line)}.data-heading h3{margin:2px 0 0;font-size:14px}.metadata-grid,.provenance dl{display:grid;grid-template-columns:minmax(110px,.8fr) minmax(0,1.2fr);gap:7px 10px;margin:0;padding:13px 14px}.metadata-grid dt,.provenance dt{font-size:9px;color:var(--muted);text-transform:capitalize}.metadata-grid dd,.provenance dd{margin:0;font-size:10px;overflow-wrap:anywhere}.list-field{padding:10px 14px;border-top:1px solid var(--line)}.list-field>b{display:block;margin-bottom:6px;font-size:9px;text-transform:capitalize}.list-field>div{display:flex;flex-wrap:wrap;gap:5px}.list-field span{padding:3px 6px;border-radius:999px;background:var(--soft);font-size:9px}.provenance{border-top:1px solid var(--line);font-size:9px}.provenance summary{padding:11px 14px;cursor:pointer;font-weight:700}.focus-actions{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 16px;border-top:1px solid var(--line);background:var(--card)}.structural-actions,.decision-actions{display:flex;gap:8px;flex-wrap:wrap}.danger{border-color:#a13f3f;color:#7d2222}@media(max-width:980px){.focus-review{inset:8px}.focus-body{grid-template-columns:1fr}.record-text{font-size:16px;padding:20px}.focus-actions{align-items:stretch;flex-direction:column}.decision-actions{justify-content:flex-end}}@media(prefers-reduced-motion:reduce){.focus-review{scroll-behavior:auto}}
</style>
