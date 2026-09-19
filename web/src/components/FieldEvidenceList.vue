<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

type Evidence={block_ids?:string[];confidence?:number;reason?:string;reviewed_by?:string};
const props=defineProps<{evidence:Record<string,Evidence>;selectedField?:string;fields?:string[]}>();
const emit=defineEmits<{select:[field:string]}>();
const i18n=useI18nStore();
const fieldNames=computed(()=>Array.from(new Set([...(props.fields||[]),...Object.keys(props.evidence||{})])).filter(Boolean).sort());
function select(field:string){emit("select",props.selectedField===field?"":field)}
</script>
<template>
  <ul v-if="fieldNames.length" class="evidence-list" :aria-label="i18n.t('pdf_corpus.field_evidence','Field evidence')">
    <li v-for="field in fieldNames" :key="field">
      <button type="button" :aria-pressed="props.selectedField===field" :class="{active:props.selectedField===field}" @click="select(String(field))">
        <b>{{field}}</b>
        <span v-if="props.evidence?.[field]">{{Math.round(Number(props.evidence[field]?.confidence||0)*100)}}% · {{(props.evidence[field]?.block_ids||[]).join(', ')||i18n.t('pdf_corpus.no_source_bound','no source block bound')}}</span>
        <span v-else>{{i18n.t('pdf_corpus.no_source_bound','no source block bound')}}</span>
        <small v-if="props.evidence?.[field]?.reason">{{props.evidence[field]?.reason}}</small>
      </button>
    </li>
  </ul>
  <p v-else class="help">{{i18n.t('pdf_corpus.no_evidence','No field evidence recorded.')}}</p>
</template>
<style scoped>
.evidence-list{list-style:none;padding:0;display:grid;gap:8px;margin:8px 0 0}.evidence-list li{margin:0}.evidence-list button{width:100%;display:grid;gap:2px;padding:7px;background:var(--soft);border:1px solid transparent;border-radius:7px;text-align:start;color:inherit;cursor:pointer}.evidence-list button.active{border-color:var(--accent)}.evidence-list button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}.evidence-list b{font-size:.8125rem}.evidence-list span,.evidence-list small,.help{font-size:.8125rem;color:var(--muted)}
</style>
