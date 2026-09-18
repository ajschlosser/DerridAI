<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { RecordSizingPolicy } from "../types/corpus";
const props=defineProps<{modelValue:RecordSizingPolicy;disabled?:boolean}>();
const emit=defineEmits<{(event:"update:modelValue",value:RecordSizingPolicy):void}>();
const i18n=useI18nStore();
const low=computed(()=>Math.max(0,Number(props.modelValue.preferred_record_chars)-Number(props.modelValue.record_length_tolerance)));
const high=computed(()=>Number(props.modelValue.preferred_record_chars)+Number(props.modelValue.record_length_tolerance));
function patch(key:keyof RecordSizingPolicy,event:Event){
  const raw=Number((event.target as HTMLInputElement).value);
  if(!Number.isFinite(raw))return;
  const next={...props.modelValue,[key]:Math.round(raw)};
  if(next.long_record_chars<next.preferred_record_chars+next.record_length_tolerance)next.long_record_chars=next.preferred_record_chars+next.record_length_tolerance;
  if(next.absolute_record_chars<next.long_record_chars)next.absolute_record_chars=next.long_record_chars;
  emit("update:modelValue",next);
}
</script>
<template>
  <fieldset class="record-sizing" :disabled="disabled" aria-describedby="record-sizing-help">
    <legend>{{i18n.t('pdf_corpus.record_sizing.title','Record sizing')}}</legend>
    <p id="record-sizing-help" class="help">{{i18n.t('pdf_corpus.record_sizing.help','Length guides retrieval-sized topology but never overrides attribution or semantic integrity. The builder aims for the preferred range and permits longer coherent exceptions when needed.')}}</p>
    <div class="primary-grid">
      <label for="corpus-preferred-chars"><span>{{i18n.t('pdf_corpus.record_sizing.preferred','Preferred record length')}}</span><input id="corpus-preferred-chars" class="control" type="number" min="600" max="12000" step="50" :value="modelValue.preferred_record_chars" @input="patch('preferred_record_chars',$event)"><small>{{i18n.tf('pdf_corpus.record_sizing.preferred_range','Target range: about {low}–{high} characters.',{low:low.toLocaleString(),high:high.toLocaleString()})}}</small></label>
      <label for="corpus-tolerance-chars"><span>{{i18n.t('pdf_corpus.record_sizing.tolerance','Preferred flexibility')}}</span><input id="corpus-tolerance-chars" class="control" type="number" min="50" max="2000" step="25" :value="modelValue.record_length_tolerance" @input="patch('record_length_tolerance',$event)"><small>{{i18n.t('pdf_corpus.record_sizing.tolerance_help','Allows clean semantic seams slightly before or after the target.')}}</small></label>
    </div>
    <details>
      <summary>{{i18n.t('pdf_corpus.record_sizing.advanced','Advanced exception limits')}}</summary>
      <div class="advanced-grid">
        <label for="corpus-long-chars"><span>{{i18n.t('pdf_corpus.record_sizing.long','Long-record exception')}}</span><input id="corpus-long-chars" class="control" type="number" min="1200" max="24000" step="100" :value="modelValue.long_record_chars" @input="patch('long_record_chars',$event)"><small>{{i18n.t('pdf_corpus.record_sizing.long_help','A coherent thought may run this long when no good seam exists near the preferred range.')}}</small></label>
        <label for="corpus-absolute-chars"><span>{{i18n.t('pdf_corpus.record_sizing.absolute','Absolute safety ceiling')}}</span><input id="corpus-absolute-chars" class="control" type="number" min="1800" max="48000" step="100" :value="modelValue.absolute_record_chars" @input="patch('absolute_record_chars',$event)"><small>{{i18n.t('pdf_corpus.record_sizing.absolute_help','Only a safety ceiling. The builder may flag review if satisfying it would break a protected attribution or syntax transition.')}}</small></label>
      </div>
    </details>
  </fieldset>
</template>
<style scoped>
.record-sizing{margin:0;border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:grid;gap:8px;background:var(--card);min-inline-size:0}.record-sizing legend{padding-inline:4px;font-size:10px;font-weight:800}.help{margin:0;color:var(--muted);font-size:8px;line-height:1.45}.primary-grid,.advanced-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.record-sizing label{display:grid;gap:4px;font-size:9px;font-weight:700}.record-sizing small{font-size:8px;line-height:1.35;color:var(--muted);font-weight:500}.record-sizing details{border-block-start:1px solid var(--line);padding-block-start:7px}.record-sizing summary{cursor:pointer;font-size:8px;font-weight:800;color:var(--muted)}.advanced-grid{margin-block-start:8px}@media(max-width:720px){.primary-grid,.advanced-grid{grid-template-columns:1fr}}
</style>
