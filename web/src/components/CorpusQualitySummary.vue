<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
const props=defineProps<{build:Record<string,any>}>();
const i18n=useI18nStore();
const validation=computed(()=>props.build.validation||{});
const topology=computed(()=>props.build.topology_quality||props.build.topology_validation||{});
const coverage=computed(()=>Math.round(Number((topology.value.source_coverage??validation.value.coverage)??0)*100));
const unresolved=computed(()=>Number(props.build.boundary_review_count||props.build.segmentation_unresolved_regions?.length||0));
const metadataDone=computed(()=>Number(props.build.metadata_completed||0));
const metadataTotal=computed(()=>Number(props.build.metadata_total||props.build.record_count||0));
const preferred=computed(()=>Number(topology.value.policy?.preferred_record_chars||props.build.record_sizing_policy?.preferred_record_chars||topology.value.preferred_record_chars||1750));
const tolerance=computed(()=>Number(topology.value.policy?.record_length_tolerance||props.build.record_sizing_policy?.record_length_tolerance||topology.value.record_length_tolerance||200));
const range=computed(()=>`${Math.max(0,preferred.value-tolerance.value).toLocaleString()}–${(preferred.value+tolerance.value).toLocaleString()}`);
</script>
<template>
  <section class="quality" :aria-labelledby="`quality-${build.build_id||'current'}`">
    <div class="quality-head"><div><b :id="`quality-${build.build_id||'current'}`">{{i18n.t('pdf_corpus.quality.title','Build quality')}}</b><small>{{i18n.t('pdf_corpus.quality.help','Quality gates summarize topology, record sizing, metadata completion, and source fidelity before publication.')}}</small></div></div>
    <dl>
      <div><dt>{{i18n.t('pdf_corpus.quality.segmentation','Topology')}}</dt><dd><b>{{Number(build.boundary_count||0).toLocaleString()}}</b> {{i18n.t('pdf_corpus.quality.boundaries','boundaries')}}<span :data-tone="unresolved?'warning':'ok'">{{unresolved?i18n.tf('pdf_corpus.quality.unresolved','{count} to review',{count:unresolved}):i18n.t('pdf_corpus.quality.resolved','Resolved')}}</span></dd></div>
      <div><dt>{{i18n.t('pdf_corpus.quality.record_size','Record size')}}</dt><dd><b>{{Number(topology.median_record_chars||0).toLocaleString()}}</b> {{i18n.t('pdf_corpus.quality.median_chars','median chars')}}<span :data-tone="Number(topology.records_over_long_limit||0)?'warning':'ok'">{{i18n.tf('pdf_corpus.quality.target_range','target {range} · P90 {p90}',{range,p90:Number(topology.p90_record_chars||0).toLocaleString()})}}</span></dd></div>
      <div><dt>{{i18n.t('pdf_corpus.quality.source','Source fidelity')}}</dt><dd><b>{{(topology.source_coverage??validation.coverage)==null?'—':`${coverage}%`}}</b> {{i18n.t('pdf_corpus.quality.accounted','accounted for')}}<span :data-tone="topology.source_conservation_valid===false||validation.source_valid===false?'warning':'ok'">{{topology.source_conservation_valid===false?i18n.t('pdf_corpus.quality.attention','Needs attention'):i18n.t('pdf_corpus.quality.passed','Conserved')}}</span></dd></div>
      <div><dt>{{i18n.t('pdf_corpus.quality.metadata','Metadata')}}</dt><dd><b>{{metadataDone.toLocaleString()}} / {{metadataTotal.toLocaleString()}}</b> {{i18n.t('pdf_corpus.quality.records_complete','records complete')}}<span :data-tone="Number(build.needs_review_count||0)?'warning':'ok'">{{i18n.tf('pdf_corpus.quality.need_review','{count} need review',{count:Number(build.needs_review_count||0)})}}</span></dd></div>
    </dl>
    <p v-if="topology.record_count" class="detail">{{i18n.tf('pdf_corpus.quality.size_detail','P10 {p10} · median {median} · P90 {p90} · max {max} · {over} above preferred range · {long} long exception(s)',{p10:Number(topology.p10_record_chars||0).toLocaleString(),median:Number(topology.median_record_chars||0).toLocaleString(),p90:Number(topology.p90_record_chars||0).toLocaleString(),max:Number(topology.max_record_chars||0).toLocaleString(),over:Number(topology.records_over_preferred_range||0).toLocaleString(),long:Number(topology.records_over_long_limit||0).toLocaleString()})}}</p>
  </section>
</template>
<style scoped>
.quality{border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:grid;gap:9px;background:var(--card)}.quality-head>div{display:grid;gap:2px}.quality-head b{font-size:.8125rem}.quality-head small,.detail{font-size:.8125rem;color:var(--muted)}dl{margin:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}dl>div{border-inline-start:2px solid var(--line);padding-inline-start:9px;display:grid;gap:3px}dt{font-size:.8125rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:800}dd{margin:0;display:grid;gap:2px;font-size:.8125rem;color:var(--muted)}dd>b{font-size:13px;color:var(--text)}dd span{font-weight:700}dd span[data-tone="ok"]::before{content:"✓ ";}dd span[data-tone="warning"]::before{content:"! ";}.detail{margin:0;border-block-start:1px solid var(--line);padding-block-start:7px;line-height:1.4}@media(max-width:900px){dl{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){dl{grid-template-columns:1fr}}
</style>
