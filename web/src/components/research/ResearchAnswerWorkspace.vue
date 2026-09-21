<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchJob, ResearchResult } from "../../types/research";
import { researchJobDetail } from "./researchI18n";

const props=withDefaults(defineProps<{job?:ResearchJob|null;result?:ResearchResult|null;busy?:boolean;canGrade?:boolean}>(),{job:null,result:null,busy:false,canGrade:true});
const emit=defineEmits<{copy:[];grade:[];rerun:[];details:[];evidence:[index:number]}>();
const i18n=useI18nStore();
type AnswerBlock = { kind:"heading"|"paragraph"|"ordered"|"unordered"; text?:string; items?:string[] };
function cleanInline(value:string){return value.replace(/^\*\*(.+)\*\*$/,"$1").trim()}
function parseBodyBlock(value:string):AnswerBlock[]{
  const block=value.trim();
  if(!block)return [];
  const heading=block.match(/^#{1,4}\s+(.+)$/s);
  if(heading)return [{kind:"heading",text:cleanInline(heading[1])}];
  const lines=block.split(/\n/).map(line=>line.trim()).filter(Boolean);
  if(lines.length&&lines.every(line=>/^\d+[.)]\s+/.test(line)))return [{kind:"ordered",items:lines.map(line=>line.replace(/^\d+[.)]\s+/,""))}];
  if(lines.length&&lines.every(line=>/^[-*•]\s+/.test(line)))return [{kind:"unordered",items:lines.map(line=>line.replace(/^[-*•]\s+/,""))}];
  return [{kind:"paragraph",text:block}];
}
const answerBlocks=computed<AnswerBlock[]>(()=>{
  const source=String(props.result?.answer||"").trim();
  if(!source)return [];
  const output:AnswerBlock[]=[];
  for(const raw of source.split(/\n{2,}/)){
    const block=raw.trim();
    if(!block)continue;
    const cited=block.match(/^\*\*Works Cited\*\*\s*(.*)$/is);
    if(cited){
      output.push({kind:"heading",text:i18n.t("research.works_cited","Works Cited")});
      if(cited[1]?.trim())output.push(...parseBodyBlock(cited[1]));
      continue;
    }
    output.push(...parseBodyBlock(block));
  }
  return output;
});

type TextSegment = { text:string; evidenceIndex?:number };
function citedSegments(value:string):TextSegment[]{
  const citations=(props.result?.evidence||[])
    .map((item,index)=>({citation:String(item.inline_citation||"").trim(),index}))
    .filter(item=>item.citation)
    .sort((a,b)=>b.citation.length-a.citation.length);
  if(!citations.length)return [{text:value}];
  const escaped=citations.map(item=>item.citation.replace(/[.*+?^${}()|[\]\\]/g,"\\$&"));
  const pattern=new RegExp(`(${escaped.join("|")})`,"g");
  return value.split(pattern).filter(Boolean).map(text=>{
    const match=citations.find(item=>item.citation===text);
    return match?{text,evidenceIndex:match.index}:{text};
  });
}
const runDetail=computed(()=>props.job?researchJobDetail(props.job,(key,fallback)=>i18n.t(key,fallback),i18n.locale):"");
const statusLabel=computed(()=>{
  if(!props.job)return "";
  if(props.job.status==="completed")return i18n.t('research.complete','Complete');
  if(props.job.status==="failed")return i18n.t('research.failed','Failed');
  if(props.job.status==="cancelled")return i18n.t('research.cancelled','Cancelled');
  if(props.job.status==="queued")return i18n.t('research.queued','Queued');
  return i18n.t('research.running','Running');
});
</script>

<template>
  <section class="research-answer-workspace card" aria-live="polite">
    <template v-if="result?.answer">
      <header class="research-answer-heading">
        <div><span class="research-answer-kicker">{{i18n.t('research.answer','Answer')}}</span><h2>{{result.prompt||job?.prompt||i18n.t('research.answer','Answer')}}</h2><p>{{result.provider||job?.provider}} · {{result.model||job?.model}}<template v-if="result.elapsed_seconds"> · {{Number(result.elapsed_seconds).toFixed(2)}}s</template></p></div>
        <div class="research-answer-actions">
          <button class="btn" type="button" @click="emit('copy')"><AppIcon name="copy"/>{{i18n.t('research.copy_answer','Copy answer')}}</button>
          <button v-if="canGrade" class="btn" type="button" @click="emit('grade')"><AppIcon name="spark"/>{{i18n.t('research.grade','Analyze & grade')}}</button>
          <button class="btn" type="button" @click="emit('details')"><AppIcon name="history"/>{{i18n.t('research.run_details','Run details')}}</button>
        </div>
      </header>
      <div v-if="result.warnings?.length" class="research-answer-warning" role="status"><p v-for="warning in result.warnings" :key="warning">{{warning}}</p></div>
      <article class="research-answer-prose">
        <template v-for="(block,index) in answerBlocks" :key="index">
          <h3 v-if="block.kind==='heading'">{{block.text}}</h3>
          <ol v-else-if="block.kind==='ordered'"><li v-for="(item,itemIndex) in block.items" :key="itemIndex"><template v-for="(segment,segmentIndex) in citedSegments(item)" :key="segmentIndex"><button v-if="segment.evidenceIndex!=null" class="research-inline-citation" type="button" :aria-label="`${i18n.t('research.inspect_evidence','Inspect evidence for')} ${segment.text}`" @click="emit('evidence',segment.evidenceIndex)">{{segment.text}}</button><template v-else>{{segment.text}}</template></template></li></ol>
          <ul v-else-if="block.kind==='unordered'"><li v-for="(item,itemIndex) in block.items" :key="itemIndex"><template v-for="(segment,segmentIndex) in citedSegments(item)" :key="segmentIndex"><button v-if="segment.evidenceIndex!=null" class="research-inline-citation" type="button" :aria-label="`${i18n.t('research.inspect_evidence','Inspect evidence for')} ${segment.text}`" @click="emit('evidence',segment.evidenceIndex)">{{segment.text}}</button><template v-else>{{segment.text}}</template></template></li></ul>
          <p v-else><template v-for="(segment,segmentIndex) in citedSegments(block.text||'')" :key="segmentIndex"><button v-if="segment.evidenceIndex!=null" class="research-inline-citation" type="button" :aria-label="`${i18n.t('research.inspect_evidence','Inspect evidence for')} ${segment.text}`" @click="emit('evidence',segment.evidenceIndex)">{{segment.text}}</button><template v-else>{{segment.text}}</template></template></p>
        </template>
      </article>
      <footer class="research-answer-footer">
        <span>{{result.evidence?.length||0}} {{i18n.t('research.evidence_records','evidence records')}}</span>
        <span v-if="result.response_cache?.record_id">{{i18n.t('research.cached','Cached')}}</span>
        <button class="research-text-action" type="button" @click="emit('rerun')">{{i18n.t('research.rerun','Re-run with these parameters')}}</button>
      </footer>
    </template>

    <template v-else-if="job">
      <div class="research-run-state" :class="job.status">
        <div class="research-run-orb" aria-hidden="true"><span></span></div>
        <div><span class="research-answer-kicker">{{statusLabel}}</span><h2>{{job.prompt||i18n.t('research.research_in_progress','Research in progress')}}</h2><p>{{runDetail}}</p></div>
      </div>
      <div v-if="job.status==='failed'" class="research-answer-warning danger" role="alert">{{job.fatal_error||i18n.t('research.run_failed','The Research run failed.')}}</div>
    </template>

    <template v-else>
      <div class="research-answer-empty">
        <div aria-hidden="true">∴</div>
        <h2>{{i18n.t('research.answer_waiting','Your research answer will appear here')}}</h2>
        <p>{{i18n.t('research.answer_waiting_help','Ask a question above. The answer stays in the workspace with its evidence rather than opening in a modal.')}}</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.research-answer-kicker {
  display: block;
  margin-bottom: 3px;
  color: var(--accent-fg);
  font-size: .8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .06em;
}
.research-answer-prose {
  max-width: 960px;
  padding: 28px 34px 36px;
  color: var(--text);
  font: 15.5px/1.75 Georgia,"Times New Roman",serif;
}
.research-answer-prose p {
  margin: 0 0 1.2em;
  white-space: pre-line;
}
.research-answer-prose h3 {
  margin: 1.8em 0 .55em;
  font: 700 15px/1.3 system-ui,-apple-system,"Segoe UI",sans-serif;
  color: var(--text);
}
.research-run-state {
  min-height: 430px;
  display: grid;
  grid-template-columns: 52px minmax(0,1fr);
  align-content: center;
  align-items: center;
  justify-content: center;
  gap: 14px;
  max-width: 700px;
  margin: auto;
  padding: 44px;
}
.research-run-state h2 {
  margin: 2px 0 4px;
  font-size: 1.125rem;
}
.research-run-state p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.research-run-orb {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--ui-accent-soft);
}
.research-run-orb span {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: var(--ui-accent);
  animation: research-pulse 1.4s ease-in-out infinite;
}
@media (max-width:860px) {
  .research-answer-prose {
    padding: 23px 22px 30px;
  }
}
@media (max-width:560px) {
  .research-answer-prose {
    font-size: 0.9375rem;
    line-height: 1.7;
    padding: 20px 17px 27px;
  }
}
.research-answer-prose ol,
.research-answer-prose ul {
  margin: 0 0 1.35em;
  padding-left: 1.55em;
}
.research-answer-prose li {
  margin: .38em 0;
  padding-left: .16em;
}
.research-answer-prose li::marker {
  color: var(--muted);
  font-family: system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size: .85em;
  font-weight: 700;
}
.research-inline-citation {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  margin: 0 .08em;
  padding: 0 .28em;
  border: 0;
  border-radius: 5px;
  background: var(--ui-accent-soft);
  color: var(--accent-fg);
  font: 700 .9em/1.2 system-ui,-apple-system,"Segoe UI",sans-serif;
  vertical-align: baseline;
  cursor: pointer;
}
.research-inline-citation:hover {
  box-shadow: inset 0 0 0 1px var(--ui-accent-border);
}
.research-inline-citation:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
@media (prefers-reduced-motion:reduce) {
  .research-run-orb span {
    animation: none;
  }
}
</style>
